#!/usr/bin/env python3
"""Canonicalize PACA Dokumenta project management as a local Sigil witness.

This carrier binds main sigilbook's PACA Dokumenta V6 line to a resident
PACA Pandoc / PACA Quarto project-management plan. It emits source evidence
only: no GitHub API, no workflow dispatch, no Git mutation, no provider IO, and
no Pandoc or Quarto render execution.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Iterable


SCHEMA_ID = "SIGIL_QUARTO_ACTIONS_PACA_DOKUMENTA_PROJECT_MANAGEMENT_V1"
DOKUMENTA_SCHEMA_ID = "SIGILITAS_PACA_DOKUMENTA_VERSION_CONTROL_HYPERDAG_V6"
CLEARANCE_SCHEMA_ID = "SIGIL_QUARTO_ACTIONS_EDITORIAL_WORKFLOW_CLEARANCE_V1"
PROTECTED_PI = "PIORNALEGO_ES_CANON"
MAX_BOUND = 3

SIGILBOOK_BASE_ANCHORS = (
    "README.md",
    "INDEX_SIGIL_BOOK.md",
    "pyproject.toml",
)

DOKUMENTA_V6_ANCHORS = (
    "docs/runtime/SIGILITAS_PACA_DOKUMENTA_VERSION_CONTROL_HYPERDAG_V6.md",
    "pipelines/pacapdg/sigilitas_paca_dokumenta_version_control_hyperdag_v6.pacapdg",
    "registry/sigilitas_paca_dokumenta_version_control_hyperdag_v6.yaml",
    "sigilapi/sigilitas_paca_dokumenta_version_control_hyperdag_v6.py",
    "witness/SIGILITAS_PACA_DOKUMENTA_VERSION_CONTROL_HYPERDAG_V6.local_validation.json",
)

PACA_RENDER_MARKERS = (
    "sigil4pandoc",
    "sigil4quarto",
    "PACA_PANDOC_AST_PROJECT",
    "PACA_QUARTO_PROJECT",
)

DOKUMENTA_INVARIANTS = (
    "V1_HISTORY_PRESERVED",
    "V2_PERSISTENT_LINEAGE_SELECTED",
    "V5_PARENT_SYSTEM_PRESERVED",
    "PACA_DOKUMENTA_FIRST_GOVERNS",
    "SEMANTIC_HYPERDAG_NE_CAUSAL_DAG",
    "PACAPDG_NE_UAP",
    "CAPABILITIES_INTERSECT",
    "CHECKPOINTS_APPEND_ONLY",
    "CANONICAL_POINTER_NE_IDENTITY_COLLAPSE",
    "VERSION_CONTROL_NE_HISTORY_REWRITE",
    "GIT_MERGE_NE_SEMANTIC_CANONICALIZATION",
    "SAFE_REPLAY_REQUIRED",
)

CANONICAL_VERSION_BINDINGS = (
    (
        "PACA_DOKUMENTA_PERSISTENT_LEARNING_SUBSYSTEM_V1",
        "1.0.0",
        "HISTORICAL",
        "preserve v1 as historical source without erasure",
    ),
    (
        "PACA_DOKUMENTA_PERSISTENT_BIBLIOTECA_LEARNING_V2",
        "2.0.0-source",
        "PERSISTENT_CANONICAL_LINEAGE",
        "select v2 as the persistent learning lineage",
    ),
    (
        "SIGILITAS_SYSTEM_FINAL_PACA_DOKUMENTA_QUARTO_PANDOC_EPOCH_V5",
        "5.0.0",
        "AGGREGATE_PARENT",
        "keep v5 as exact predecessor aggregate",
    ),
    (
        "PYDANTIKA_TYPED_POLICY_KOKOMPI_MEMORIA_PACA_DOKUMENTA_FIRST_V1",
        "1.0.0-candidate",
        "POLICY_GATE",
        "retain PACA Dokumenta First as the policy gate",
    ),
    (
        "SIGILITAS_PACA_DOKUMENTA_VERSION_CONTROL_HYPERDAG_V6",
        "6.0.0",
        "CANONICAL_CONSOLIDATION",
        "canonicalize V6 as the consolidation pointer",
    ),
)

PROJECT_NODES = (
    ("source.sigilbook.main", 0, ()),
    ("source.resident.clearance", 0, ()),
    ("dokumenta.v6.canonical_source", 1, ("source.sigilbook.main",)),
    ("project.intake.index", 1, ("source.resident.clearance",)),
    ("pacapandoc.ast.catalog", 2, ("dokumenta.v6.canonical_source",)),
    ("pacaquarto.structure.catalog", 2, ("dokumenta.v6.canonical_source",)),
    ("pydantika.policy.gate", 2, ("dokumenta.v6.canonical_source", "project.intake.index")),
    (
        "project.management.plan",
        3,
        ("pydantika.policy.gate", "pacapandoc.ast.catalog", "pacaquarto.structure.catalog"),
    ),
    (
        "render.plan",
        3,
        ("pacapandoc.ast.catalog", "pacaquarto.structure.catalog", "project.intake.index"),
    ),
    ("checkpoint.safe_replay", 3, ("project.management.plan", "render.plan", "pydantika.policy.gate")),
)

DOCUMENT_SUFFIXES = {
    ".qmd": "quarto_document",
    ".md": "markdown_document",
    ".ipynb": "notebook_document",
    ".bib": "bibliography",
    ".csl": "citation_style",
    ".lua": "pandoc_filter",
    ".yaml": "yaml_manifest",
    ".yml": "yaml_manifest",
}

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".sigil-test-deps",
    ".tox",
    ".venv",
    "node_modules",
    "__pycache__",
}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    path: str | None = None

    def as_dict(self) -> dict[str, str]:
        payload = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.path:
            payload["path"] = self.path
        return payload


def _as_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"expected boolean, got {value!r}")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _repo_rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _git_commit(path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _extract_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", text)
    if not match:
        return None
    return match.group(1).strip().strip("'\"")


def _extract_assignment_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}\s*=\s*(.+?)\s*$", text)
    if not match:
        return None
    return match.group(1).strip().strip("'\"")


def _anchor_report(root: Path, relpaths: tuple[str, ...], *, severity: str) -> tuple[dict[str, bool], list[Finding]]:
    report: dict[str, bool] = {}
    findings: list[Finding] = []
    for relpath in relpaths:
        exists = (root / relpath).is_file()
        report[relpath] = exists
        if not exists:
            findings.append(Finding(severity, "SOURCE_ANCHOR_MISSING", "required source anchor missing", relpath))
    return report, findings


def _load_clearance(path: Path | None, require_clearance: bool) -> tuple[dict[str, Any], list[Finding]]:
    if path is None:
        severity = "HOLD" if require_clearance else "WARN"
        return {"provided": False}, [
            Finding(severity, "CLEARANCE_WITNESS_ABSENT", "clear-workflows witness was not provided")
        ]
    if not path.is_file():
        return {"provided": True, "path": str(path)}, [
            Finding("HOLD", "CLEARANCE_WITNESS_MISSING", "clearance witness path does not exist", str(path))
        ]
    try:
        payload = json.loads(_read_text(path))
    except json.JSONDecodeError as exc:
        return {"provided": True, "path": str(path)}, [
            Finding("REJECT", "CLEARANCE_WITNESS_INVALID_JSON", f"clearance witness is invalid JSON: {exc}", str(path))
        ]
    verdict = payload.get("verdict")
    findings: list[Finding] = []
    if verdict != "ADMIT_SOURCE_PLAN":
        findings.append(
            Finding("HOLD", "CLEARANCE_WITNESS_NOT_ADMITTED", f"clearance verdict is {verdict!r}", str(path))
        )
    schema_id = payload.get("schema_id")
    if schema_id != CLEARANCE_SCHEMA_ID:
        findings.append(
            Finding("WARN", "CLEARANCE_SCHEMA_ID_UNEXPECTED", f"clearance schema id is {schema_id!r}", str(path))
        )
    return {
        "provided": True,
        "path": str(path),
        "schema_id": schema_id,
        "verdict": verdict,
        "resident": payload.get("resident", {}),
    }, findings


def _scan_dokumenta_source(sigilbook_path: Path) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    base_anchors, base_findings = _anchor_report(sigilbook_path, SIGILBOOK_BASE_ANCHORS, severity="REJECT")
    v6_anchors, v6_findings = _anchor_report(sigilbook_path, DOKUMENTA_V6_ANCHORS, severity="HOLD")
    findings.extend(base_findings)
    findings.extend(v6_findings)

    source_text_parts: list[str] = []
    for relpath in SIGILBOOK_BASE_ANCHORS + DOKUMENTA_V6_ANCHORS:
        path = sigilbook_path / relpath
        if path.is_file():
            source_text_parts.append(_read_text(path))
    source_text = "\n".join(source_text_parts)
    pyproject_text = _read_text(sigilbook_path / "pyproject.toml") if (sigilbook_path / "pyproject.toml").is_file() else ""

    marker_report: dict[str, bool] = {}
    for marker in PACA_RENDER_MARKERS:
        present = marker in source_text
        marker_report[marker] = present
        if not present:
            findings.append(
                Finding("HOLD", "PACA_RENDER_MARKER_MISSING", f"PACA Pandoc/Quarto marker missing: {marker}")
            )

    invariant_report: dict[str, bool] = {}
    for invariant in DOKUMENTA_INVARIANTS:
        present = invariant in source_text
        invariant_report[invariant] = present
        if not present:
            findings.append(
                Finding("HOLD", "DOKUMENTA_INVARIANT_MISSING", f"Dokumenta V6 invariant missing: {invariant}")
            )

    registry_path = sigilbook_path / "registry/sigilitas_paca_dokumenta_version_control_hyperdag_v6.yaml"
    registry_text = _read_text(registry_path) if registry_path.is_file() else ""
    schema_id = _extract_scalar(registry_text, "schema_id")
    protected_pi = _extract_scalar(registry_text, "protected_pi")
    if schema_id != DOKUMENTA_SCHEMA_ID:
        findings.append(Finding("HOLD", "DOKUMENTA_SCHEMA_ID_MISSING", "Dokumenta V6 schema id is absent"))
    if protected_pi != PROTECTED_PI:
        findings.append(Finding("HOLD", "PROTECTED_PI_MISSING", "protected Pi canon marker is absent"))

    version_bindings: list[dict[str, Any]] = []
    for schema_id_expected, version_expected, role, consolidation_rule in CANONICAL_VERSION_BINDINGS:
        schema_present = schema_id_expected in source_text
        version_present = version_expected in source_text
        if not schema_present:
            findings.append(
                Finding(
                    "HOLD",
                    "SIGILITAS_VERSION_SCHEMA_MISSING",
                    f"Sigilitas consolidation schema missing: {schema_id_expected}",
                )
            )
        if not version_present:
            findings.append(
                Finding(
                    "HOLD",
                    "SIGILITAS_VERSION_VALUE_MISSING",
                    f"Sigilitas consolidation version missing: {schema_id_expected} {version_expected}",
                )
            )
        version_bindings.append(
            {
                "schema_id": schema_id_expected,
                "version": version_expected,
                "role": role,
                "schema_present": schema_present,
                "version_present": version_present,
                "consolidation_rule": consolidation_rule,
            }
        )

    return {
        "path": str(sigilbook_path),
        "commit": _git_commit(sigilbook_path),
        "base_anchors": base_anchors,
        "dokumenta_v6_anchors": v6_anchors,
        "registry": {
            "schema_id": schema_id,
            "version": _extract_scalar(registry_text, "version"),
            "status": _extract_scalar(registry_text, "status"),
            "source_main_sha": _extract_scalar(registry_text, "source_main_sha"),
            "protected_pi": protected_pi,
        },
        "sigil_runtime": {
            "project_name": _extract_assignment_scalar(pyproject_text, "name"),
            "project_version": _extract_assignment_scalar(pyproject_text, "version"),
            "requires_python": _extract_assignment_scalar(pyproject_text, "requires-python"),
        },
        "sigilitas_version_bindings": version_bindings,
        "paca_render_markers": marker_report,
        "invariants": invariant_report,
    }, findings


def _walk_project_documents(project_root: Path, max_documents: int) -> dict[str, Any]:
    documents: list[dict[str, str]] = []
    quarto_projects: list[str] = []
    pandoc_filters: list[str] = []

    if not project_root.exists() or not project_root.is_dir():
        return {
            "path": str(project_root),
            "exists": False,
            "documents": documents,
            "document_count": 0,
            "truncated": False,
            "quarto_projects": quarto_projects,
            "pandoc_filters": pandoc_filters,
        }

    truncated = False
    for candidate in sorted(project_root.rglob("*")):
        if any(part in SKIP_DIRS for part in candidate.parts):
            continue
        if not candidate.is_file():
            continue
        rel = _repo_rel(candidate, project_root)
        suffix = candidate.suffix.lower()
        name = candidate.name.lower()
        if name in {"_quarto.yml", "_quarto.yaml", "quarto.yml", "quarto.yaml"}:
            quarto_projects.append(rel)
        if suffix == ".lua":
            pandoc_filters.append(rel)
        kind = DOCUMENT_SUFFIXES.get(suffix)
        if kind is None and name not in {"_quarto.yml", "_quarto.yaml", "quarto.yml", "quarto.yaml"}:
            continue
        if len(documents) >= max_documents:
            truncated = True
            continue
        documents.append(
            {
                "path": rel,
                "kind": kind or "quarto_project_config",
                "status": "BACKLOG",
                "lane": "intake",
            }
        )

    return {
        "path": str(project_root),
        "exists": True,
        "documents": documents,
        "document_count": len(documents),
        "truncated": truncated,
        "quarto_projects": quarto_projects[:max_documents],
        "pandoc_filters": pandoc_filters[:max_documents],
    }


def _project_graph(max_fanin: int, max_fanout: int, max_layer: int) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    nodes = {name: {"layer": layer, "needs": tuple(needs)} for name, layer, needs in PROJECT_NODES}
    children: dict[str, list[str]] = defaultdict(list)
    indegree = {name: 0 for name in nodes}

    for name, node in nodes.items():
        needs = node["needs"]
        if len(needs) > max_fanin:
            findings.append(
                Finding("REJECT", "PROJECT_FANIN_EXCEEDS_BOUND", f"{name} has fan-in {len(needs)}, max {max_fanin}")
            )
        layer = node["layer"]
        if layer > max_layer:
            findings.append(
                Finding("REJECT", "PROJECT_LAYER_EXCEEDS_BOUND", f"{name} reaches layer {layer}, max {max_layer}")
            )
        for need in needs:
            if need not in nodes:
                findings.append(Finding("REJECT", "PROJECT_NEED_UNKNOWN", f"{name} needs unknown node {need}"))
                continue
            if nodes[need]["layer"] > layer:
                findings.append(
                    Finding("REJECT", "PROJECT_LAYER_REVERSAL", f"{name} depends on later-layer node {need}")
                )
            children[need].append(name)
            indegree[name] += 1

    for name in sorted(nodes):
        fanout = len(children[name])
        if fanout > max_fanout:
            findings.append(
                Finding("REJECT", "PROJECT_FANOUT_EXCEEDS_BOUND", f"{name} has fan-out {fanout}, max {max_fanout}")
            )

    queue: deque[str] = deque(sorted(name for name, degree in indegree.items() if degree == 0))
    visited: list[str] = []
    while queue:
        current = queue.popleft()
        visited.append(current)
        for child in sorted(children[current]):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    cyclic = len(visited) != len(nodes)
    if cyclic:
        findings.append(Finding("REJECT", "PROJECT_GRAPH_CYCLIC", "Dokumenta project graph must be acyclic"))

    return {
        "nodes": {
            name: {
                "layer": node["layer"],
                "needs": list(node["needs"]),
                "fanin": len(node["needs"]),
                "fanout": len(children[name]),
            }
            for name, node in sorted(nodes.items())
        },
        "topological_order": visited,
        "cyclic": cyclic,
    }, findings


def _render_tool_paths(check_tool_paths: bool) -> dict[str, Any]:
    if not check_tool_paths:
        return {
            "checked": False,
            "pandoc_on_path": None,
            "quarto_on_path": None,
            "pandoc_executed": False,
            "quarto_executed": False,
        }
    return {
        "checked": True,
        "pandoc_on_path": shutil.which("pandoc") is not None,
        "quarto_on_path": shutil.which("quarto") is not None,
        "pandoc_executed": False,
        "quarto_executed": False,
    }


def _severity_verdict(findings: Iterable[Finding]) -> str:
    severities = {item.severity for item in findings}
    if "REJECT" in severities:
        return "REJECT"
    if "HOLD" in severities:
        return "HOLD"
    return "ADMIT_SOURCE_PLAN"


def _append_github_output(verdict: str, witness_path: Path) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        handle.write(f"verdict={verdict}\n")
        handle.write(f"witness-path={witness_path.as_posix()}\n")


def _project_management_plan(args: argparse.Namespace, inventory: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": args.project_id,
        "project_name": args.project_name,
        "owner": args.owner,
        "status_taxonomy": ["BACKLOG", "READY", "IN_PROGRESS", "BLOCKED", "REVIEW", "CANONICALIZED"],
        "lanes": [
            {
                "id": "intake",
                "kind": "PACA_DOKUMENTA_FIRST",
                "purpose": "classify project documents before render planning",
            },
            {
                "id": "pacapandoc",
                "kind": "PACA_PANDOC_AST_PROJECT",
                "purpose": "plan Pandoc AST and filter responsibilities",
            },
            {
                "id": "pacaquarto",
                "kind": "PACA_QUARTO_PROJECT",
                "purpose": "plan Quarto structure, profiles, books, sites, and notebooks",
            },
            {
                "id": "pydantika",
                "kind": "PACA_DOKUMENTA_FIRST_POLICY_GATE",
                "purpose": "hold/reject unsafe identity, history, authority, or capability drift",
            },
            {
                "id": "safe_replay",
                "kind": "SAFE_REPLAY_CHECKPOINT",
                "purpose": "record append-only replay state before any external authority acts",
            },
        ],
        "milestones": [
            {
                "id": "m0.source_alignment",
                "exit": "sigilbook main and Dokumenta V6 anchors are present",
            },
            {
                "id": "m1.project_inventory",
                "exit": "resident document inventory is indexed as backlog items",
            },
            {
                "id": "m2.policy_gate",
                "exit": "Pydantika policy admits the source plan without capability amplification",
            },
            {
                "id": "m3.render_plan",
                "exit": "Pandoc and Quarto render intentions are typed without execution",
            },
            {
                "id": "m4.safe_replay",
                "exit": "append-only replay witness is ready for Sigil KLI/QLI authority",
            },
        ],
        "inventory": inventory,
        "pacapandoc": {
            "mode": "AST_PROJECT_PLAN",
            "managed_artifacts": ["markdown_document", "bibliography", "citation_style", "pandoc_filter"],
            "pandoc_executed": False,
        },
        "pacaquarto": {
            "mode": "QUARTO_PROJECT_PLAN",
            "managed_artifacts": ["quarto_project_config", "quarto_document", "notebook_document"],
            "quarto_executed": False,
        },
        "dependency_policy": {
            "capabilities": "INTERSECTION",
            "ambient_union": False,
            "canonical_pointer_is_projection": True,
            "version_control_is_append_only": True,
        },
    }


def _version_consolidation_plan(source: dict[str, Any]) -> dict[str, Any]:
    bindings = source.get("sigilitas_version_bindings", [])
    admitted = all(
        bool(binding.get("schema_present")) and bool(binding.get("version_present"))
        for binding in bindings
    )
    return {
        "mode": "SIGIL_SIGILITAS_VERSION_RECONCILIATION_FOR_CONSOLIDACION",
        "canonical_schema_id": DOKUMENTA_SCHEMA_ID,
        "canonical_version": "6.0.0",
        "canonical_pointer": {
            "points_to": DOKUMENTA_SCHEMA_ID,
            "identity_collapse": False,
            "history_rewrite": False,
            "git_merge": False,
        },
        "bindings": bindings,
        "runtime": source.get("sigil_runtime", {}),
        "admitted_for_consolidation": admitted,
        "consolidation_order": [
            "preserve historical v1",
            "select persistent v2",
            "bind aggregate v5 as parent",
            "apply Dokumenta First policy v1",
            "project canonical V6 without erasing earlier versions",
        ],
    }


def build_witness(args: argparse.Namespace) -> tuple[dict[str, Any], list[Finding]]:
    sigilbook_path = Path(args.sigilbook_path).resolve()
    resident_path = Path(args.resident_path).resolve()
    project_root = (resident_path / args.project_path).resolve()
    clearance_path = Path(args.clearance_witness).resolve() if args.clearance_witness else None
    findings: list[Finding] = []

    dokumenta_source, source_findings = _scan_dokumenta_source(sigilbook_path)
    findings.extend(source_findings)

    clearance, clearance_findings = _load_clearance(clearance_path, args.require_clearance)
    findings.extend(clearance_findings)

    if not project_root.exists() or not project_root.is_dir():
        findings.append(Finding("HOLD", "PROJECT_PATH_MISSING", "resident project path does not exist", str(project_root)))

    graph, graph_findings = _project_graph(args.max_fanin, args.max_fanout, args.max_layer)
    findings.extend(graph_findings)

    if args.execute_pandoc or args.execute_quarto or args.mutate_repository or args.provider_io or args.start_scheduler:
        findings.append(
            Finding(
                "REJECT",
                "EXTERNAL_AUTHORITY_REQUESTED",
                "this carrier only canonicalizes source project plans; execution belongs to authorized Sigil layers",
            )
        )

    inventory = _walk_project_documents(project_root, args.max_documents)
    render_tools = _render_tool_paths(args.check_tool_paths)
    project_management = _project_management_plan(args, inventory)
    version_consolidation = _version_consolidation_plan(dokumenta_source)

    counts: dict[str, int] = defaultdict(int)
    for finding in findings:
        counts[finding.severity] += 1
    verdict = _severity_verdict(findings)

    witness = {
        "schema_id": SCHEMA_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_id": args.project_id,
        "verdict": verdict,
        "resident": {
            "path": str(resident_path),
            "repository": os.environ.get("GITHUB_REPOSITORY", resident_path.name),
            "subsystem": "sigil-quarto-actions",
            "role": "paca-dokumenta-project-management",
            "mode": "thin",
        },
        "source": {
            "sigilbook": dokumenta_source,
            "clearance": clearance,
            "github_connector_policy": {
                "github_api_called_by_carrier": False,
                "gh_cli_executed_by_carrier": False,
                "workflow_dispatched_by_carrier": False,
                "repository_mutated_by_carrier": False,
                "codex_github_connector_owns_authorized_repository_io": True,
            },
        },
        "sigilitas_version_consolidation": version_consolidation,
        "project_management": project_management,
        "render_tool_paths": render_tools,
        "contracts": {
            "protected_pi": PROTECTED_PI,
            "dokumenta_schema_id": DOKUMENTA_SCHEMA_ID,
            "canonicalization": {
                "semantic_hyperdag_ne_causal_dag": True,
                "pacapdg_ne_uap": True,
                "canonical_pointer_ne_identity_collapse": True,
                "version_control_ne_history_rewrite": True,
                "semantic_canonicalization_ne_git_merge": True,
                "capabilities_by_intersection": True,
                "safe_replay_required": True,
            },
            "allowed_operations": ["DESCRIBE", "READ", "VALIDATE", "PLAN", "CANONICALIZE_SOURCE_PLAN"],
            "forbidden_operations": [
                "workflow_dispatch",
                "github_api_call",
                "gh_cli_mutation",
                "git_merge",
                "git_push",
                "repository_mutation",
                "pandoc_render",
                "quarto_render",
                "provider_io",
                "scheduler_start",
            ],
            "bounded_contextual_layers": {
                "allowed_layers": [0, 1, 2, 3],
                "max_fanin": args.max_fanin,
                "max_fanout": args.max_fanout,
                "max_layer": args.max_layer,
            },
            "thin_quazris_projection": True,
            "thick_runtime_not_started": True,
            "sigil_kli_qli_cli_owns_typed_plan": True,
        },
        "project_graph": graph,
        "finding_counts": dict(sorted(counts.items())),
        "findings": [finding.as_dict() for finding in findings],
    }
    return witness, findings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sigilbook-path", default="../sigilbook")
    parser.add_argument("--resident-path", default=".")
    parser.add_argument("--project-path", default=".")
    parser.add_argument("--clearance-witness", default="")
    parser.add_argument("--witness-output", default="sigil-dokumenta-project-witness.json")
    parser.add_argument("--project-id", default="paca.dokumenta.project.local")
    parser.add_argument("--project-name", default="PACA Dokumenta Project Management")
    parser.add_argument("--owner", default=os.environ.get("USERNAME") or os.environ.get("USER") or "codex-local-owner")
    parser.add_argument("--max-documents", type=int, default=200)
    parser.add_argument("--max-fanin", type=int, default=MAX_BOUND)
    parser.add_argument("--max-fanout", type=int, default=MAX_BOUND)
    parser.add_argument("--max-layer", type=int, default=MAX_BOUND)
    parser.add_argument("--require-clearance", type=_as_bool, default=True)
    parser.add_argument("--fail-on-hold", type=_as_bool, default=True)
    parser.add_argument("--check-tool-paths", type=_as_bool, default=False)
    parser.add_argument("--execute-pandoc", type=_as_bool, default=False)
    parser.add_argument("--execute-quarto", type=_as_bool, default=False)
    parser.add_argument("--mutate-repository", type=_as_bool, default=False)
    parser.add_argument("--provider-io", type=_as_bool, default=False)
    parser.add_argument("--start-scheduler", type=_as_bool, default=False)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    for numeric_name in ("max_fanin", "max_fanout", "max_layer"):
        value = getattr(args, numeric_name)
        if value < 0 or value > MAX_BOUND:
            print(f"{numeric_name.replace('_', '-')} must be in the bounded 0..3 range", file=sys.stderr)
            return 64
    if args.max_documents < 1:
        print("max-documents must be at least 1", file=sys.stderr)
        return 64

    witness, _findings = build_witness(args)
    witness_path = Path(args.witness_output).resolve()
    witness_path.parent.mkdir(parents=True, exist_ok=True)
    witness_path.write_text(json.dumps(witness, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")

    verdict = witness["verdict"]
    _append_github_output(verdict, witness_path)
    print(json.dumps({"verdict": verdict, "witness_path": str(witness_path)}, sort_keys=True))
    if verdict == "REJECT":
        return 2
    if verdict == "HOLD" and args.fail_on_hold:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
