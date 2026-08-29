#!/usr/bin/env python3
"""Clear Sigil editorial workflows against local sigilbook/Koko SDK anchors.

This checker is intentionally thin: Python standard library only, local files
only, and no GitHub API or workflow-dispatch authority. It emits a typed witness
that a resident repository can hand to the Sigil KLI/QLI/CLI and Codex GitHub
connector layer for separately authorized repository operations.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterable


SCHEMA_ID = "SIGIL_QUARTO_ACTIONS_EDITORIAL_WORKFLOW_CLEARANCE_V1"
KOKO_SCHEMA_ID = "SIGILITAS_KOKO_SDK_KONNEKTIA_VIRTUAL_KLI_PACA_HABILIDAD_V1"
KNEXT_SCHEMA_ID = "KNEXT_KLI_QLI_CLI_KQC_VXA_VVA_BRIDGES_V1"
PROTECTED_PI = "PIORNALEGO_ES_CANON"
DEFAULT_MAX_FAN = 3
DEFAULT_MAX_LAYER = 3

SIGILBOOK_REQUIRED_FILES = (
    "README.md",
    "INDEX_SIGIL_BOOK.md",
    "pyproject.toml",
)

KOKO_REQUIRED_FILES = (
    "docs/glue/SIGILITAS_KOKO_SDK_KONNEKTIA_VIRTUAL_KLI_PACA_HABILIDAD_V1.md",
    "registry/sigilitas_koko_sdk_konnektia_virtual_kli_paca_habilidad_v1.yaml",
    "sigilapi/sigilitas_koko_sdk_konnektia_virtual_kli_paca_habilidad_v1.py",
    "sigilapi/knext_kli_qli_cli_kqc_vxa_vva_bridges_v1.py",
)

KLI_BASELINE_MARKERS = (
    "KLI",
    "QLI",
    "KQC",
)

KLI_EXTENDED_MARKERS = (
    "sigil-sigilitas-kli-qli-kqc-virtual-cli",
    "pydantic-settings",
    "sigil4cpython",
)

GITHUB_API_MARKERS = (
    "api.github.com",
    "gh api",
    "github.event.workflow_run",
)

MUTATING_GH_MARKERS = (
    "gh workflow run",
    "gh run rerun",
    "gh repo delete",
    "gh pr merge",
    "git push --force",
    "git push -f",
)


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


@dataclass
class WorkflowGraph:
    path: str
    jobs: dict[str, tuple[str, ...]] = field(default_factory=dict)
    fanin: dict[str, int] = field(default_factory=dict)
    fanout: dict[str, int] = field(default_factory=dict)
    layers: dict[str, int] = field(default_factory=dict)
    cyclic: bool = False
    unknown_needs: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "job_count": len(self.jobs),
            "jobs": {
                job_id: {
                    "needs": list(needs),
                    "fanin": self.fanin.get(job_id, 0),
                    "fanout": self.fanout.get(job_id, 0),
                    "layer": self.layers.get(job_id),
                }
                for job_id, needs in sorted(self.jobs.items())
            },
            "cyclic": self.cyclic,
            "unknown_needs": {
                job_id: list(needs)
                for job_id, needs in sorted(self.unknown_needs.items())
            },
        }


def _repo_rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


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


def _discover_workflow_files(layer: Path) -> list[Path]:
    if not layer.exists() or not layer.is_dir():
        return []
    files: list[Path] = []
    for suffix in ("*.yml", "*.yaml"):
        files.extend(layer.rglob(suffix))
    return sorted({item.resolve() for item in files})


def _line_key(line: str) -> tuple[int, str, str] | None:
    match = re.match(r"^( *)([A-Za-z0-9_.-]+):(?:\s*(.*))?$", line)
    if not match:
        return None
    return len(match.group(1)), match.group(2), match.group(3).strip()


def _parse_needs_value(value: str) -> tuple[str, ...]:
    value = value.strip()
    if not value or value.startswith("${{"):
        return ()
    if value.startswith("[") and "]" in value:
        inside = value[1 : value.index("]")]
        return tuple(
            item.strip().strip("'\"")
            for item in inside.split(",")
            if item.strip().strip("'\"")
        )
    if value.startswith(('"', "'")) and value.endswith(('"', "'")):
        value = value[1:-1]
    if re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        return (value,)
    return ()


def _parse_workflow_graph(path: Path, root: Path) -> WorkflowGraph:
    lines = _read_text(path).splitlines()
    rel = _repo_rel(path, root)
    jobs: dict[str, list[str]] = {}
    in_jobs = False
    current_job: str | None = None
    collecting_needs_for: str | None = None

    for line in lines:
        key = _line_key(line)
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if key and key[0] == 0:
            in_jobs = key[1] == "jobs"
            current_job = None
            collecting_needs_for = None
            continue
        if not in_jobs:
            continue
        if key and key[0] == 2:
            current_job = key[1]
            jobs.setdefault(current_job, [])
            collecting_needs_for = None
            continue
        if current_job is None:
            continue
        if key and key[0] >= 4 and key[1] == "needs":
            needs = _parse_needs_value(key[2])
            jobs[current_job].extend(needs)
            collecting_needs_for = current_job if not needs and not key[2] else None
            continue
        if collecting_needs_for == current_job:
            item_match = re.match(r"^ *- +([A-Za-z0-9_.-]+)\s*$", line)
            if item_match:
                jobs[current_job].append(item_match.group(1))
            elif key and key[0] <= 4:
                collecting_needs_for = None

    normalized_jobs = {
        job_id: tuple(dict.fromkeys(needs))
        for job_id, needs in jobs.items()
    }
    graph = WorkflowGraph(path=rel, jobs=normalized_jobs)
    known_jobs = set(normalized_jobs)
    unknown: dict[str, tuple[str, ...]] = {}
    fanout: dict[str, int] = {job_id: 0 for job_id in known_jobs}
    fanin: dict[str, int] = {}

    for job_id, needs in normalized_jobs.items():
        unknown_needs = tuple(item for item in needs if item not in known_jobs)
        if unknown_needs:
            unknown[job_id] = unknown_needs
        known_needs = tuple(item for item in needs if item in known_jobs)
        fanin[job_id] = len(known_needs)
        for need in known_needs:
            fanout[need] = fanout.get(need, 0) + 1

    graph.fanin = fanin
    graph.fanout = fanout
    graph.unknown_needs = unknown
    graph.layers, graph.cyclic = _compute_layers(normalized_jobs)
    return graph


def _compute_layers(jobs: dict[str, tuple[str, ...]]) -> tuple[dict[str, int], bool]:
    known_jobs = set(jobs)
    children: dict[str, list[str]] = {job_id: [] for job_id in known_jobs}
    indegree: dict[str, int] = {job_id: 0 for job_id in known_jobs}

    for job_id, needs in jobs.items():
        for need in needs:
            if need not in known_jobs:
                continue
            children[need].append(job_id)
            indegree[job_id] += 1

    queue: deque[str] = deque(sorted(job for job, degree in indegree.items() if degree == 0))
    layers = {job_id: 0 for job_id in queue}
    visited: list[str] = []
    while queue:
        current = queue.popleft()
        visited.append(current)
        for child in sorted(children[current]):
            layers[child] = max(layers.get(child, 0), layers[current] + 1)
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    cyclic = len(visited) != len(known_jobs)
    return layers, cyclic


def _workflow_policy_findings(
    path: Path,
    root: Path,
    graph: WorkflowGraph,
    *,
    max_fanin: int,
    max_fanout: int,
    max_layer: int,
) -> list[Finding]:
    text = _read_text(path)
    rel = _repo_rel(path, root)
    findings: list[Finding] = []

    if not re.search(r"(?m)^name:\s*\S", text):
        findings.append(Finding("WARN", "WORKFLOW_NAME_MISSING", "workflow has no top-level name", rel))
    if not re.search(r"(?m)^on:\s*(?:$|[\[{]|[A-Za-z])", text):
        findings.append(Finding("HOLD", "WORKFLOW_ON_MISSING", "workflow has no top-level on trigger", rel))
    if not re.search(r"(?m)^jobs:\s*$", text):
        findings.append(Finding("HOLD", "WORKFLOW_JOBS_MISSING", "workflow has no top-level jobs map", rel))
    if "pull_request_target" in text:
        findings.append(
            Finding(
                "REJECT",
                "PULL_REQUEST_TARGET_FORBIDDEN",
                "editorial clearance forbids pull_request_target authority",
                rel,
            )
        )
    lowered = text.lower()
    for marker in GITHUB_API_MARKERS:
        if marker in lowered:
            findings.append(
                Finding(
                    "REJECT",
                    "GITHUB_API_SURFACE_FORBIDDEN",
                    f"workflow references forbidden GitHub API surface: {marker}",
                    rel,
                )
            )
    for marker in MUTATING_GH_MARKERS:
        if marker in lowered:
            findings.append(
                Finding(
                    "REJECT",
                    "MUTATING_GH_PLAN_FORBIDDEN",
                    f"workflow references mutating GitHub command: {marker}",
                    rel,
                )
            )
    if "workflow_dispatch" not in text:
        findings.append(
            Finding(
                "WARN",
                "MANUAL_CLEARING_TRIGGER_ABSENT",
                "workflow has no workflow_dispatch clearing surface",
                rel,
            )
        )
    if not re.search(r"(?m)^permissions:\s*$", text):
        findings.append(
            Finding(
                "WARN",
                "EXPLICIT_PERMISSIONS_ABSENT",
                "workflow should declare top-level permissions for QQUAPP boundary clarity",
                rel,
            )
        )
    for uses_target in re.findall(r"(?m)^\s*uses:\s*([^#\s]+)", text):
        if "@" not in uses_target:
            findings.append(
                Finding("WARN", "UNPINNED_ACTION_REFERENCE", f"uses reference has no ref: {uses_target}", rel)
            )
        elif uses_target.endswith("@main") or uses_target.endswith("@master"):
            findings.append(
                Finding(
                    "WARN",
                    "FLOATING_ACTION_REFERENCE",
                    f"uses reference floats on branch: {uses_target}",
                    rel,
                )
            )
    if "actions/checkout" in text and "persist-credentials: false" not in text:
        findings.append(
            Finding(
                "WARN",
                "CHECKOUT_CREDENTIALS_PERSIST",
                "checkout should disable credential persistence unless this workflow owns a write path",
                rel,
            )
        )

    if not graph.jobs:
        return findings
    if graph.cyclic:
        findings.append(Finding("REJECT", "WORKFLOW_JOB_GRAPH_CYCLIC", "job graph must be acyclic", rel))
    if graph.unknown_needs:
        findings.append(
            Finding(
                "HOLD",
                "WORKFLOW_NEEDS_UNKNOWN_JOB",
                "job graph has needs entries outside the local jobs map",
                rel,
            )
        )
    for job_id in sorted(graph.jobs):
        fanin = graph.fanin.get(job_id, 0)
        fanout = graph.fanout.get(job_id, 0)
        layer = graph.layers.get(job_id)
        if fanin > max_fanin:
            findings.append(
                Finding(
                    "REJECT",
                    "WORKFLOW_FANIN_EXCEEDS_BOUND",
                    f"job {job_id} has fan-in {fanin}, max {max_fanin}",
                    rel,
                )
            )
        if fanout > max_fanout:
            findings.append(
                Finding(
                    "REJECT",
                    "WORKFLOW_FANOUT_EXCEEDS_BOUND",
                    f"job {job_id} has fan-out {fanout}, max {max_fanout}",
                    rel,
                )
            )
        if layer is not None and layer > max_layer:
            findings.append(
                Finding(
                    "REJECT",
                    "WORKFLOW_LAYER_EXCEEDS_BOUND",
                    f"job {job_id} reaches layer {layer}, max {max_layer}",
                    rel,
                )
            )
    return findings


def _scan_sigilbook(
    sigilbook_path: Path,
    *,
    require_koko_sdk: bool,
    subsystem_mode: str,
) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    anchors: dict[str, Any] = {
        "path": str(sigilbook_path),
        "commit": _git_commit(sigilbook_path),
        "required_files": {},
        "koko_sdk_files": {},
        "kli_baseline_markers": {},
        "kli_extended_markers": {},
        "kli_source_level": "unknown",
        "subsystem_mode": subsystem_mode,
    }
    if not sigilbook_path.exists():
        findings.append(
            Finding(
                "REJECT",
                "SIGILBOOK_PATH_MISSING",
                "main sigilbook path does not exist",
                str(sigilbook_path),
            )
        )
        return anchors, findings

    for rel in SIGILBOOK_REQUIRED_FILES:
        exists = (sigilbook_path / rel).is_file()
        anchors["required_files"][rel] = exists
        if not exists:
            findings.append(Finding("REJECT", "SIGILBOOK_ANCHOR_MISSING", "required sigilbook anchor missing", rel))

    koko_text = ""
    for rel in KOKO_REQUIRED_FILES:
        path = sigilbook_path / rel
        exists = path.is_file()
        anchors["koko_sdk_files"][rel] = exists
        if exists:
            koko_text += "\n" + _read_text(path)
        elif require_koko_sdk:
            findings.append(Finding("REJECT", "KOKO_SDK_ANCHOR_MISSING", "required Koko SDK anchor missing", rel))

    pyproject_path = sigilbook_path / "pyproject.toml"
    pyproject_text = _read_text(pyproject_path) if pyproject_path.is_file() else ""
    source_text = pyproject_text + "\n" + koko_text
    baseline_present = True
    for marker in KLI_BASELINE_MARKERS:
        present = marker in source_text
        anchors["kli_baseline_markers"][marker] = present
        if require_koko_sdk and not present:
            baseline_present = False
            findings.append(Finding("HOLD", "KLI_BASELINE_MARKER_MISSING", f"KLI/QLI baseline marker missing: {marker}"))

    extended_present = True
    for marker in KLI_EXTENDED_MARKERS:
        present = marker in source_text
        anchors["kli_extended_markers"][marker] = present
        if not present:
            extended_present = False
            findings.append(
                Finding(
                    "WARN",
                    "KLI_EXTENDED_MARKER_ABSENT",
                    f"extended local KLI/QLI marker is absent from main: {marker}",
                )
            )
    anchors["kli_source_level"] = "extended" if extended_present else ("baseline" if baseline_present else "incomplete")

    if require_koko_sdk and KOKO_SCHEMA_ID not in source_text:
        findings.append(Finding("REJECT", "KOKO_SCHEMA_ID_MISSING", "Koko SDK schema id is absent from anchors"))
    if require_koko_sdk and KNEXT_SCHEMA_ID not in source_text:
        findings.append(Finding("WARN", "KNEXT_SCHEMA_ID_MISSING", "KNEXT KLI/QLI bridge id is absent from anchors"))
    if PROTECTED_PI not in source_text:
        findings.append(Finding("HOLD", "PROTECTED_PI_MISSING", "protected Pi canon marker is absent from anchors"))

    if subsystem_mode == "thick":
        for marker in ("sigil4py", "sigil4cpython"):
            if marker not in source_text:
                findings.append(
                    Finding(
                        "REJECT",
                        "THICK_SUBSYSTEM_MARKER_MISSING",
                        f"thick subsystem mode requires source marker: {marker}",
                    )
                )
    return anchors, findings


def _load_resident_manifest(path: Path | None) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    if path is None:
        return {
            "source": "implicit",
            "residents": [
                {
                    "repository": os.environ.get("GITHUB_REPOSITORY", Path.cwd().name),
                    "subsystem": "editorial-curatorial-localized-workflows",
                    "mode": "thin",
                    "layer": 0,
                }
            ],
        }, findings
    if not path.is_file():
        return {"source": str(path), "residents": []}, [
            Finding("HOLD", "RESIDENT_MANIFEST_MISSING", "resident manifest path is absent", str(path))
        ]

    try:
        data = json.loads(_read_text(path))
    except json.JSONDecodeError as exc:
        return {"source": str(path), "residents": []}, [
            Finding("REJECT", "RESIDENT_MANIFEST_INVALID_JSON", f"resident manifest is not valid JSON: {exc}", str(path))
        ]

    residents = data.get("residents")
    if not isinstance(residents, list) or not residents:
        findings.append(
            Finding("HOLD", "RESIDENT_MANIFEST_EMPTY", "resident manifest must contain a non-empty residents list", str(path))
        )
        residents = []

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(residents):
        context = f"{path.as_posix()}#residents[{index}]"
        if not isinstance(item, dict):
            findings.append(Finding("REJECT", "RESIDENT_ENTRY_NOT_OBJECT", "resident entry must be an object", context))
            continue
        repository = item.get("repository")
        mode = item.get("mode")
        layer = item.get("layer")
        subsystem = item.get("subsystem")
        if not isinstance(repository, str) or "/" not in repository:
            findings.append(Finding("REJECT", "RESIDENT_REPOSITORY_INVALID", "resident repository must be owner/name", context))
        if mode not in {"thin", "thick"}:
            findings.append(Finding("REJECT", "RESIDENT_MODE_INVALID", "resident mode must be thin or thick", context))
        if not isinstance(layer, int) or layer < 0 or layer > DEFAULT_MAX_LAYER:
            findings.append(Finding("REJECT", "RESIDENT_LAYER_INVALID", "resident layer must be an integer 0..3", context))
        if not isinstance(subsystem, str) or not subsystem:
            findings.append(Finding("HOLD", "RESIDENT_SUBSYSTEM_MISSING", "resident subsystem name is required", context))
        normalized.append(
            {
                "repository": repository,
                "subsystem": subsystem,
                "mode": mode,
                "layer": layer,
                "localized_presheaf": item.get("localized_presheaf", True),
                "paca_estaca_effective": item.get("paca_estaca_effective", True),
            }
        )
    return {"source": str(path), "residents": normalized}, findings


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


def build_witness(args: argparse.Namespace) -> tuple[dict[str, Any], list[Finding]]:
    resident_root = Path(args.resident_path).resolve()
    sigilbook_path = Path(args.sigilbook_path).resolve()
    workflow_layer = resident_root / args.workflow_layer
    findings: list[Finding] = []

    subsystem_mode = args.subsystem_mode
    if subsystem_mode == "auto":
        subsystem_mode = "thick" if (resident_root / "pyproject.toml").exists() else "thin"

    anchors, anchor_findings = _scan_sigilbook(
        sigilbook_path,
        require_koko_sdk=args.require_koko_sdk,
        subsystem_mode=subsystem_mode,
    )
    findings.extend(anchor_findings)

    resident_manifest_path = Path(args.resident_manifest).resolve() if args.resident_manifest else None
    residents, resident_findings = _load_resident_manifest(resident_manifest_path)
    findings.extend(resident_findings)

    workflow_files = _discover_workflow_files(workflow_layer)
    if not workflow_files and args.require_localized_layer:
        findings.append(
            Finding(
                "HOLD",
                "WORKFLOW_LAYER_EMPTY",
                "localized editorial workflow layer has no workflow YAML files",
                _repo_rel(workflow_layer, resident_root),
            )
        )

    graphs: list[WorkflowGraph] = []
    for workflow_file in workflow_files:
        graph = _parse_workflow_graph(workflow_file, resident_root)
        graphs.append(graph)
        findings.extend(
            _workflow_policy_findings(
                workflow_file,
                resident_root,
                graph,
                max_fanin=args.max_fanin,
                max_fanout=args.max_fanout,
                max_layer=args.max_layer,
            )
        )

    by_severity: dict[str, int] = defaultdict(int)
    for finding in findings:
        by_severity[finding.severity] += 1
    verdict = _severity_verdict(findings)

    witness = {
        "schema_id": SCHEMA_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "resident": {
            "path": str(resident_root),
            "repository": os.environ.get("GITHUB_REPOSITORY", resident_root.name),
            "mode": subsystem_mode,
            "workflow_layer": args.workflow_layer,
        },
        "source": {
            "main_sigilbook": anchors,
            "koko_sdk_schema_id": KOKO_SCHEMA_ID,
            "knext_kli_qli_cli_schema_id": KNEXT_SCHEMA_ID,
            "github_connector_policy": {
                "github_api_called_by_checker": False,
                "gh_cli_executed_by_checker": False,
                "workflow_dispatched_by_checker": False,
                "repository_mutated_by_checker": False,
                "connector_is_kernel": False,
                "sigil_kli_qli_cli_owns_typed_plan": True,
            },
        },
        "contracts": {
            "subsystem": "sigil-quarto-actions",
            "layer": "editorial-curatorial-localized-workflows",
            "effective_sigilbook_plural_typed_subsystem": True,
            "localized_allegoric_presheaf": True,
            "localized_paca_estaca": True,
            "protected_pi": PROTECTED_PI,
            "thin_thick_typed_ir_mlir": {
                "thin": {
                    "quazris_based": True,
                    "minimal_dependencies": True,
                    "python_stdlib_only": True,
                    "mlir_emitted": False,
                    "mlir_executed": False,
                },
                "thick": {
                    "sigil4py_required": True,
                    "sigil4cpython_required": True,
                    "full_virtual_os_allowed": True,
                    "runtime_started_by_checker": False,
                },
                "selected_mode": subsystem_mode,
            },
            "bounded_contextual_layers": {
                "allowed_layers": [0, 1, 2, 3],
                "max_fanin": args.max_fanin,
                "max_fanout": args.max_fanout,
                "max_layer": args.max_layer,
            },
            "allowed_operations": ["DESCRIBE", "READ", "VALIDATE", "PLAN"],
            "forbidden_operations": [
                "workflow_dispatch",
                "workflow_rerun",
                "github_api_call",
                "repository_mutation",
                "merge",
                "external_command_execution",
            ],
        },
        "federation": residents,
        "workflow_graphs": [graph.as_dict() for graph in graphs],
        "finding_counts": dict(sorted(by_severity.items())),
        "findings": [finding.as_dict() for finding in findings],
    }
    return witness, findings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sigilbook-path", default=".", help="local path to an already-materialized main sigilbook checkout")
    parser.add_argument("--resident-path", default=".", help="local path to the resident repository being cleared")
    parser.add_argument("--workflow-layer", default=".github/workflows", help="workflow directory relative to resident path")
    parser.add_argument("--resident-manifest", default="", help="optional JSON manifest of SynthGothHub residents")
    parser.add_argument("--witness-output", default="sigil-clearance-witness.json", help="path to write the JSON witness")
    parser.add_argument("--subsystem-mode", choices=("thin", "thick", "auto"), default="thin")
    parser.add_argument("--max-fanin", type=int, default=DEFAULT_MAX_FAN)
    parser.add_argument("--max-fanout", type=int, default=DEFAULT_MAX_FAN)
    parser.add_argument("--max-layer", type=int, default=DEFAULT_MAX_LAYER)
    parser.add_argument("--require-koko-sdk", type=_as_bool, default=True)
    parser.add_argument("--require-localized-layer", type=_as_bool, default=True)
    parser.add_argument("--fail-on-hold", type=_as_bool, default=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    for numeric_name in ("max_fanin", "max_fanout", "max_layer"):
        if getattr(args, numeric_name) < 0 or getattr(args, numeric_name) > 3:
            print(f"{numeric_name.replace('_', '-')} must be in the bounded 0..3 range", file=sys.stderr)
            return 64

    witness, findings = build_witness(args)
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
