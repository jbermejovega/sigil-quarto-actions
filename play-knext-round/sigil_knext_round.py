#!/usr/bin/env python3
"""Play a bounded PACAIOGAME KNEXT round as a Sigil source-plan witness.

The carrier composes Pydantika Aprende, deploy-plan, merge-plan and play-round
without performing an external deployment, Git merge, workflow dispatch, or game
runtime launch. Real repository IO belongs to the Sigil KLI/QLI/CLI plus Codex
GitHub connector layer after a human-authorized plan exists.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable


SCHEMA_ID = "SIGIL_QUARTO_ACTIONS_PYDANTIKA_APRENDE_PACAIOGAME_KNEXT_ROUND_V1"
PROTECTED_PI = "PIORNALEGO_ES_CANON"
MAX_BOUND = 3

SIGILBOOK_ANCHORS = (
    "pyproject.toml",
    "sigilapi/knext_kli_qli_cli_kqc_vxa_vva_bridges_v1.py",
    "sigilapi/sigilitas_koko_sdk_konnektia_virtual_kli_paca_habilidad_v1.py",
    "registry/sigilitas_koko_sdk_konnektia_virtual_kli_paca_habilidad_v1.yaml",
)

PACAIOGAME_ANCHORS = (
    "sigilapi/pacaiogame_typed_action_workflow_runtime.py",
    "registry/pacaiogame_typed_action_workflow_runtime_v1.yaml",
    ".github/workflows/pacaiogame-virtual-live-deploy.yml",
    ".github/workflows/knext-pacaiogame-ir-m1.yml",
    "manifests/KNEXT_PACAIOGAME_IR_M1.yaml",
)

ROUND_NODES = (
    ("source.sigilbook.main", 0, ()),
    ("source.resident.clearance", 0, ()),
    ("pydantika.aprende", 1, ("source.sigilbook.main", "source.resident.clearance")),
    ("koko.sdk.compat", 1, ("source.sigilbook.main",)),
    ("knext.ir.localize", 2, ("pydantika.aprende", "koko.sdk.compat")),
    ("deploy.plan", 2, ("knext.ir.localize",)),
    ("merge.plan", 2, ("knext.ir.localize", "source.resident.clearance")),
    ("pacaiogame.play.round", 3, ("deploy.plan", "merge.plan", "knext.ir.localize")),
    ("checkpoint.safe_replay", 3, ("pacaiogame.play.round",)),
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


def _severity_verdict(findings: Iterable[Finding]) -> str:
    severities = {item.severity for item in findings}
    if "REJECT" in severities:
        return "REJECT"
    if "HOLD" in severities:
        return "HOLD"
    return "ADMIT_SOURCE_PLAN"


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
        finding = Finding(
            "HOLD" if require_clearance else "WARN",
            "CLEARANCE_WITNESS_ABSENT",
            "clear-workflows witness was not provided",
        )
        return {"provided": False}, [finding]
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
    if verdict != "ADMIT_SOURCE_PLAN":
        return {"provided": True, "path": str(path), "verdict": verdict}, [
            Finding("HOLD", "CLEARANCE_WITNESS_NOT_ADMITTED", f"clearance verdict is {verdict!r}", str(path))
        ]
    return {
        "provided": True,
        "path": str(path),
        "schema_id": payload.get("schema_id"),
        "verdict": verdict,
        "resident": payload.get("resident", {}),
    }, []


def _round_graph(max_fanin: int, max_fanout: int, max_layer: int) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    nodes = {name: {"layer": layer, "needs": tuple(needs)} for name, layer, needs in ROUND_NODES}
    children: dict[str, list[str]] = defaultdict(list)
    indegree = {name: 0 for name in nodes}

    for name, node in nodes.items():
        needs = node["needs"]
        if len(needs) > max_fanin:
            findings.append(
                Finding("REJECT", "ROUND_FANIN_EXCEEDS_BOUND", f"{name} has fan-in {len(needs)}, max {max_fanin}")
            )
        layer = node["layer"]
        if layer > max_layer:
            findings.append(
                Finding("REJECT", "ROUND_LAYER_EXCEEDS_BOUND", f"{name} reaches layer {layer}, max {max_layer}")
            )
        for need in needs:
            if need not in nodes:
                findings.append(Finding("REJECT", "ROUND_NEED_UNKNOWN", f"{name} needs unknown node {need}"))
                continue
            if nodes[need]["layer"] > layer:
                findings.append(
                    Finding("REJECT", "ROUND_LAYER_REVERSAL", f"{name} depends on later-layer node {need}")
                )
            children[need].append(name)
            indegree[name] += 1

    for name in sorted(nodes):
        fanout = len(children[name])
        if fanout > max_fanout:
            findings.append(
                Finding("REJECT", "ROUND_FANOUT_EXCEEDS_BOUND", f"{name} has fan-out {fanout}, max {max_fanout}")
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
        findings.append(Finding("REJECT", "ROUND_GRAPH_CYCLIC", "KNEXT round graph must be acyclic"))

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


def _append_github_output(verdict: str, witness_path: Path) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        handle.write(f"verdict={verdict}\n")
        handle.write(f"witness-path={witness_path.as_posix()}\n")


def build_witness(args: argparse.Namespace) -> tuple[dict[str, Any], list[Finding]]:
    sigilbook_path = Path(args.sigilbook_path).resolve()
    resident_path = Path(args.resident_path).resolve()
    clearance_path = Path(args.clearance_witness).resolve() if args.clearance_witness else None
    findings: list[Finding] = []

    sigilbook_anchors, sigilbook_findings = _anchor_report(sigilbook_path, SIGILBOOK_ANCHORS, severity="REJECT")
    pacaiogame_anchors, pacaiogame_findings = _anchor_report(sigilbook_path, PACAIOGAME_ANCHORS, severity="HOLD")
    findings.extend(sigilbook_findings)
    findings.extend(pacaiogame_findings)

    clearance, clearance_findings = _load_clearance(clearance_path, args.require_clearance)
    findings.extend(clearance_findings)

    round_graph, graph_findings = _round_graph(args.max_fanin, args.max_fanout, args.max_layer)
    findings.extend(graph_findings)

    if args.execute_deploy or args.execute_merge or args.start_game_runtime:
        findings.append(
            Finding(
                "REJECT",
                "EXTERNAL_AUTHORITY_REQUESTED",
                "this carrier only emits source plans; execution belongs to KLI/QLI plus authorized connector IO",
            )
        )

    counts: dict[str, int] = defaultdict(int)
    for finding in findings:
        counts[finding.severity] += 1
    verdict = _severity_verdict(findings)

    witness = {
        "schema_id": SCHEMA_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "round_id": args.round_id,
        "verdict": verdict,
        "player": args.player,
        "resident": {
            "path": str(resident_path),
            "repository": os.environ.get("GITHUB_REPOSITORY", resident_path.name),
            "subsystem": "sigil-quarto-actions",
            "role": "editorial-curatorial-pacaiogame-knext-round",
        },
        "source": {
            "sigilbook_path": str(sigilbook_path),
            "sigilbook_commit": _git_commit(sigilbook_path),
            "sigilbook_anchors": sigilbook_anchors,
            "pacaiogame_anchors": pacaiogame_anchors,
            "clearance": clearance,
        },
        "pydantika_aprende": {
            "learns_from": ["clear-workflows", "main_sigilbook", "koko_sdk", "knext_ir_m1"],
            "mode": "bounded_source_learning",
            "hidden_memory": False,
            "model_retraining_implied": False,
            "repository_authority": False,
        },
        "deploy_merge_play": {
            "deploy": {"kind": "DEPLOY_PLAN", "executed": False, "authority": False},
            "merge": {"kind": "MERGE_PLAN", "git_merge_executed": False, "authority": False},
            "play": {"kind": "PACAIOGAME_KNEXT_ROUND", "runtime_started": False, "source_round": True},
        },
        "contracts": {
            "protected_pi": PROTECTED_PI,
            "allowed_operations": ["DESCRIBE", "READ", "VALIDATE", "PLAN", "PLAY_SOURCE_ROUND"],
            "forbidden_operations": [
                "workflow_dispatch",
                "github_api_call",
                "git_merge",
                "git_push",
                "deployment",
                "game_runtime_start",
            ],
            "bounded_contextual_layers": {
                "allowed_layers": [0, 1, 2, 3],
                "max_fanin": args.max_fanin,
                "max_fanout": args.max_fanout,
                "max_layer": args.max_layer,
            },
            "thin_quazris_projection": True,
            "thick_runtime_not_started": True,
            "codex_github_connector_authority_external": True,
            "sigil_kli_qli_cli_owns_typed_plan": True,
        },
        "round_graph": round_graph,
        "finding_counts": dict(sorted(counts.items())),
        "findings": [finding.as_dict() for finding in findings],
    }
    return witness, findings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sigilbook-path", default="../sigilbook")
    parser.add_argument("--resident-path", default=".")
    parser.add_argument("--clearance-witness", default="")
    parser.add_argument("--witness-output", default="sigil-knext-round-witness.json")
    parser.add_argument("--round-id", default="knext.pacaiogame.round.local")
    parser.add_argument("--player", default=os.environ.get("USERNAME") or os.environ.get("USER") or "codex-local-player")
    parser.add_argument("--max-fanin", type=int, default=MAX_BOUND)
    parser.add_argument("--max-fanout", type=int, default=MAX_BOUND)
    parser.add_argument("--max-layer", type=int, default=MAX_BOUND)
    parser.add_argument("--require-clearance", type=_as_bool, default=True)
    parser.add_argument("--fail-on-hold", type=_as_bool, default=True)
    parser.add_argument("--execute-deploy", type=_as_bool, default=False)
    parser.add_argument("--execute-merge", type=_as_bool, default=False)
    parser.add_argument("--start-game-runtime", type=_as_bool, default=False)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    for numeric_name in ("max_fanin", "max_fanout", "max_layer"):
        value = getattr(args, numeric_name)
        if value < 0 or value > MAX_BOUND:
            print(f"{numeric_name.replace('_', '-')} must be in the bounded 0..3 range", file=sys.stderr)
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
