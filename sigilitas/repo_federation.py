"""Virtual repository sessions projected into read-only federated STATIK memory."""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any


SHA40 = re.compile(r"^[0-9a-f]{40}$")


def digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def virtual_repo_session(repository: str, head_sha: str, pr_tree: dict[str, Any]) -> dict[str, Any]:
    panics = []
    if not SHA40.fullmatch(head_sha):
        panics.append({"code": "REPOSITORY_HEAD_WITNESS_MISSING", "verdict": "HOLD"})
    if pr_tree.get("verdict") != "ADMIT":
        panics.append({"code": "PR_TREE_NOT_ADMITTED", "verdict": "HOLD"})
    tree_digest = pr_tree.get("tree_digest")
    repo_bearer = f"repo:{repository}"
    session_bearer = f"session:{repository}:{head_sha}"
    memory_bearer = f"statik-memory:{repository}:{head_sha}"
    matrix_slot = f"repo-matrix-slot:{digest(repository)[:16]}"
    omega = digest({"repository": repository, "head_sha": head_sha, "tree_digest": tree_digest})
    body = {
        "schema_id": "SIGILITAS_SYNTHGOTHHUB_REPO_FEDERATION_V1",
        "virtual_session": {
            "type": "VirtualRepoSessionType",
            "bearer_id": session_bearer,
            "repository_bearer_id": repo_bearer,
            "literal_bearer_equality": False,
            "head_sha": head_sha,
            "tree_digest": tree_digest,
            "effects": ["DESCRIBE", "READ", "VALIDATE", "PLAN"],
        },
        "embodied_statik_memory": {
            "type": "EmbodiedSTATIKMemoryType",
            "bearer_id": memory_bearer,
            "session_bearer_id": session_bearer,
            "materialized_state_is_append_only": False,
            "checkpoint_ledger_is_monotonic": True,
            "checkpoint": f"checkpoint:sha256:{omega}",
        },
        "repository_matrix": {
            "type": "RepositoryMatrixType",
            "slot_id": matrix_slot,
            "member_repository": repository,
            "member_identity_preserved": True,
        },
        "federation": {
            "type": "TypedGitHubFederationType",
            "root_repository": "jbermejovega/sigilbook",
            "member_slot": matrix_slot,
            "capability_composition": "INTERSECTION",
            "authority_amplification": False,
        },
        "cloud_projection": {
            "type": "SynthGothHubCloudType",
            "omega_witness": f"omega:sha256:{omega}",
            "physical_cloud_claimed": False,
            "github_identity_collapsed": False,
        },
        "panics": panics,
        "verdict": "HOLD" if panics else "ADMIT",
        "invariants": {
            "pi_fixed": True,
            "safe_replay": True,
            "hidden_sync": False,
            "repository_mutated": False,
            "runtime_authority": False,
        },
    }
    body["receipt_digest"] = digest(body)
    return body


__all__ = ["virtual_repo_session"]
