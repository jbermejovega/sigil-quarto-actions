#!/usr/bin/env python3
"""Generate a policy-gated PACADEX snapshot from an accepted GitHub event."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any


SCHEMA_ID = "SIGILITAS_PIBI_PACADEX_V1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
USES = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)")


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def accepted_event(name: str, ref: str, payload: dict[str, Any]) -> tuple[bool, str]:
    if name == "push" and ref == "refs/heads/main":
        return True, "ACCEPTED_MAIN_COMMIT"
    if name == "release" and payload.get("action") == "published":
        return True, "ACCEPTED_PUBLISHED_RELEASE"
    if name == "workflow_dispatch":
        return False, "MANUAL_INSPECTION_ONLY"
    return False, "UNACCEPTED_GITHUB_EVENT"


def inspect_workflows(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    workflow_root = root / ".github" / "workflows"
    for path in sorted((*workflow_root.glob("*.yml"), *workflow_root.glob("*.yaml"))):
        text = path.read_text(encoding="utf-8")
        if "permissions:" not in text:
            findings.append({"file": str(path.relative_to(root)), "code": "PERMISSIONS_UNDECLARED"})
        if "pull_request_target:" in text:
            findings.append({"file": str(path.relative_to(root)), "code": "PR_TARGET_REQUIRES_TRUST_REVIEW"})
        for line in text.splitlines():
            match = USES.match(line)
            if not match:
                continue
            target = match.group(1)
            if target.startswith("./"):
                continue
            ref = target.rsplit("@", 1)[-1] if "@" in target else ""
            if not SHA40.fullmatch(ref):
                findings.append({"file": str(path.relative_to(root)), "code": "ACTION_NOT_PINNED_FULL_SHA", "target": target})
        if "/latest/download/" in text:
            findings.append({"file": str(path.relative_to(root)), "code": "LATEST_DOWNLOAD_NOT_DIGEST_PINNED"})
    return findings


def sessions() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes = [
        {"id": "event", "actor": "KOKOMPI_EVENT_READER", "effect": "READ", "predecessors": [], "capabilities": ["github_event_read"]},
        {"id": "rag", "actor": "KOKOMPI_RAG_INSPECTOR", "effect": "READ", "predecessors": ["event"], "capabilities": ["workflow_read"]},
        {"id": "policy", "actor": "KOKOMPI_POLICY_KEEPER", "effect": "VALIDATE", "predecessors": ["event", "rag"], "capabilities": ["policy_validate"]},
        {"id": "pacadex", "actor": "KOKOMPI_PACADEX_BUILDER", "effect": "PLAN", "predecessors": ["policy"], "capabilities": ["index_plan"]},
        {"id": "mcp", "actor": "KOKOMPI_MCP_EXPOSER", "effect": "DESCRIBE", "predecessors": ["pacadex"], "capabilities": ["resource_describe"]},
    ]
    bunches = [
        {"id": "shared-policy", "connective": "&", "left": ["event"], "right": ["rag", "policy"], "structural_sharing": True},
        {"id": "separated-output", "connective": "*", "left": ["pacadex"], "right": ["mcp"], "structural_sharing": False},
    ]
    return nodes, bunches


def validate_session_tree(nodes: list[dict[str, Any]], bunches: list[dict[str, Any]]) -> None:
    ids = {node["id"] for node in nodes}
    if len(ids) != len(nodes):
        raise ValueError("DUPLICATE_SESSION")
    effects = {"READ", "VALIDATE", "PLAN", "DESCRIBE"}
    if any(node["effect"] not in effects for node in nodes):
        raise ValueError("AMBIENT_EFFECT")
    if any(not set(node["predecessors"]).issubset(ids) for node in nodes):
        raise ValueError("UNKNOWN_PREDECESSOR")
    seen: set[str] = set()
    while len(seen) < len(ids):
        ready = {node["id"] for node in nodes if node["id"] not in seen and set(node["predecessors"]).issubset(seen)}
        if not ready:
            raise ValueError("SESSION_DAG_CYCLE")
        seen |= ready
    by_id = {node["id"]: set(node["capabilities"]) for node in nodes}
    for bunch in bunches:
        if bunch["connective"] == "*":
            left = set().union(*(by_id[x] for x in bunch["left"]))
            right = set().union(*(by_id[x] for x in bunch["right"]))
            if left & right or bunch["structural_sharing"]:
                raise ValueError("MULTIPLICATIVE_RESOURCE_ALIAS")


def build(root: Path, event_name: str, ref: str, sha: str, repository: str, payload: dict[str, Any]) -> dict[str, Any]:
    admitted, reason = accepted_event(event_name, ref, payload)
    nodes, bunches = sessions()
    validate_session_tree(nodes, bunches)
    findings = inspect_workflows(root)
    project = {
        "type": "GitHubProjectType",
        "repository": repository,
        "ref": ref,
        "commit_sha": sha,
        "event": event_name,
        "policy": "SIGILITAS_GLOBAL_KOKOMPICRACIA_POLICY_V1",
    }
    resources = [
        {"uri": "sigil://pacadex/project", "type": "GitHubProjectType"},
        {"uri": f"sigil://pacadex/commit/{sha}", "type": "GitCommitType"},
        {"uri": "sigil://pacadex/workflows", "type": "WorkflowRAGInspection"},
        {"uri": "sigil://pacadex/policies/global", "type": "GlobalPolicyType"},
        {"uri": "sigil://pacadex/kokompis", "type": "PluralKokompiSessionTree"},
    ]
    body = {
        "schema_id": SCHEMA_ID,
        "verdict": "ADMIT" if admitted else "HOLD",
        "reason": reason,
        "project": project,
        "session_tree": {"logic": "piBI", "nodes": nodes, "bunches": bunches},
        "rag_inspection": {"source_bound": True, "hidden_learning": False, "findings": findings},
        "mcp": {"self_exposed": True, "effects": ["DESCRIBE", "READ", "VALIDATE", "PLAN"], "resources": resources},
        "release_policy": {
            "publisher": "SEMVER_RELEASE_TAGS_AND_MAJOR_ALIAS",
            "consumer": "FULL_COMMIT_SHA_PREFERRED",
            "immutable_release_tags": True,
            "default_branch_reference": False,
        },
        "invariants": {
            "pi_fixed": True,
            "runtime_authority": False,
            "repository_mutated": False,
            "accepted_receipts_only": True,
            "global_policy_precedes_role_policy": True,
        },
    }
    body["snapshot_digest"] = digest(body)
    return body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--event-path", type=Path, required=True)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", type=Path, default=Path("pacadex-out"))
    args = parser.parse_args()
    if not SHA40.fullmatch(args.sha):
        raise SystemExit("commit SHA must be full length")
    payload = json.loads(args.event_path.read_text(encoding="utf-8"))
    snapshot = build(args.root, args.event_name, args.ref, args.sha, args.repository, payload)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "pacadex.json").write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output / "mcp-resources.json").write_text(json.dumps(snapshot["mcp"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = {"verdict": snapshot["verdict"], "snapshot_digest": snapshot["snapshot_digest"], "commit_sha": args.sha, "safe_replay": True, "repository_mutated": False}
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
