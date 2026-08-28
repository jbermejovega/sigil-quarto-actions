"""Deterministic typing of a materialized GitHub PR worktree."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


IGNORED_PARTS = {".git", "__pycache__", ".pytest_cache", "pacadex-out"}


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(raw.encode()).hexdigest()


def artifact_type(path: str) -> str:
    p = PurePosixPath(path)
    name = p.name
    if path.startswith(".github/workflows/"):
        return "GitHubWorkflowType"
    if path == ".github/dependabot.yml":
        return "DependencyUpdatePolicyType"
    if path.startswith("policies/"):
        return "GlobalPolicyType"
    if path.startswith("registry/"):
        return "TypeRegistryType"
    if path.startswith("sigilitas/") and p.suffix == ".py":
        return "SigilitasRuntimeCarrierType"
    if path.startswith("tests/") and p.suffix == ".py":
        return "ExecutableTestWitnessType"
    if path.startswith("witness/") and name.endswith(".paca_task.json"):
        return "PacaTaskEnvelopeType"
    if path.startswith("witness/") and name.endswith(".paca_task_receipt.json"):
        return "SafeReplayReceiptType"
    if path.startswith("witness/"):
        return "ValidationWitnessType"
    if path.startswith("docs/"):
        return "DocumentationProjectionType"
    return "PrimitiveArtifactType"


def capabilities(kind: str) -> list[str]:
    table = {
        "GitHubWorkflowType": ["workflow_describe", "workflow_validate"],
        "DependencyUpdatePolicyType": ["dependency_policy_read"],
        "GlobalPolicyType": ["global_policy_read"],
        "TypeRegistryType": ["type_registry_read"],
        "SigilitasRuntimeCarrierType": ["carrier_read", "carrier_validate"],
        "ExecutableTestWitnessType": ["test_describe", "test_plan"],
        "PacaTaskEnvelopeType": ["task_validate"],
        "SafeReplayReceiptType": ["receipt_read"],
        "ValidationWitnessType": ["witness_read"],
        "DocumentationProjectionType": ["documentation_read"],
        "PrimitiveArtifactType": ["artifact_read"],
    }
    return table[kind]


def _paths(root: Path, selected: Iterable[str] | None) -> list[Path]:
    if selected is not None:
        candidates = [root / PurePosixPath(path) for path in selected]
    else:
        candidates = list(root.rglob("*"))
    return sorted(
        (p for p in candidates if p.is_file() and not p.is_symlink() and not (set(p.relative_to(root).parts) & IGNORED_PARTS)),
        key=lambda p: p.relative_to(root).as_posix(),
    )


def type_pr_tree(root: Path, selected: Iterable[str] | None = None) -> dict[str, Any]:
    root = root.resolve()
    files = _paths(root, selected)
    file_nodes: list[dict[str, Any]] = []
    directory_paths: set[str] = {"."}
    for file_path in files:
        rel = file_path.relative_to(root).as_posix()
        raw = file_path.read_bytes()
        kind = artifact_type(rel)
        file_nodes.append({
            "node_id": f"file:{rel}",
            "path": rel,
            "node_type": kind,
            "content_digest": f"sha256:{sha256(raw).hexdigest()}",
            "size_bytes": len(raw),
            "capability_scope": capabilities(kind),
            "identity_distinct": True,
        })
        parent = PurePosixPath(rel).parent
        while str(parent) not in {"", "."}:
            directory_paths.add(parent.as_posix())
            parent = parent.parent
    directory_nodes = [
        {"node_id": f"dir:{path}", "path": path, "node_type": "WorkTreeDirectoryType", "identity_distinct": True}
        for path in sorted(directory_paths)
    ]
    edges: list[dict[str, str]] = []
    for node in directory_nodes:
        if node["path"] != ".":
            parent = PurePosixPath(node["path"]).parent.as_posix()
            edges.append({"source": f"dir:{parent}", "target": node["node_id"], "edge_type": "DIRECTORY_CONTAINS"})
    for node in file_nodes:
        parent = PurePosixPath(node["path"]).parent.as_posix()
        edges.append({"source": f"dir:{parent}", "target": node["node_id"], "edge_type": "DIRECTORY_CONTAINS"})

    quanta = []
    previous: str | None = None
    for index, node in enumerate(file_nodes):
        quantum_id = f"q{index:04d}"
        quanta.append({
            "quantum_id": quantum_id,
            "effect": "TYPE_ARTIFACT",
            "target": node["node_id"],
            "predecessors": [previous] if previous else [],
        })
        previous = quantum_id

    body = {
        "schema_id": "SIGILITAS_WHOLE_PR_TREE_TYPED_V1",
        "scope": "MATERIALIZED_WORKTREE" if selected is None else "SELECTED_PR_TREE",
        "root": {"node_id": "dir:.", "node_type": "ProjectType"},
        "directories": directory_nodes,
        "files": file_nodes,
        "relations": edges,
        "session": {
            "logic": "piBI",
            "additive": {"connective": "&", "shares": ["project_context", "provenance"]},
            "multiplicative": {"connective": "*", "separates": [node["node_id"] for node in file_nodes]},
        },
        "causal_projection": {
            "type": "DAG<FluxQuantumTyped>",
            "quanta": quanta,
            "acyclic": True,
            "max_fan_in": 1,
            "max_fan_out": 1,
            "single_effect": True,
        },
        "invariants": {
            "all_files_typed": True,
            "identities_distinct": True,
            "pi_fixed": True,
            "safe_replay": True,
            "repository_mutated": False,
            "runtime_authority": False,
        },
        "verdict": "ADMIT" if file_nodes else "HOLD",
        "panics": [] if file_nodes else [{"code": "EMPTY_TREE_WITNESS", "verdict": "HOLD"}],
    }
    body["tree_digest"] = digest(body)
    return body


__all__ = ["artifact_type", "type_pr_tree"]
