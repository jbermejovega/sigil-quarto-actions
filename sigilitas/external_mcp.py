"""Canonical read-only MCP exposition for typed KOKOMPI repository sessions."""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from sigilitas.editorial_factorization import canonical_editorial_codicex


def digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def canonical_mcp_exposure(
    repository: str,
    head_sha: str,
    agents: list[dict[str, Any]],
    pr_tree: dict[str, Any],
    federation: dict[str, Any],
) -> dict[str, Any]:
    registered = sorted({agent["actor"] for agent in agents})
    _editorial_codicex, editorial_receipt = canonical_editorial_codicex(repository, head_sha)
    resources = [
        {"uri": "sigil://mcp/paca-quarto/project", "type": "PACAQuartoProjectionType", "source_bound": True},
        {"uri": "sigil://mcp/paca-quarto/editorial-factorization", "type": "PACAQuartoEditorialFactorizationType", "digest": editorial_receipt["receipt_digest"], "verdict": editorial_receipt["verdict"]},
        {"uri": "sigil://mcp/paca-pandoc/ast", "type": "PACAPandocASTProjectionType", "source_bound": True},
        {"uri": "sigil://mcp/sigilbook/live", "type": "LiveSigilbookType", "source_bound": True},
        {"uri": "sigil://mcp/hyperjarra/jauria", "type": "HyperJarraJauriaType", "source_bound": True},
        {"uri": "sigil://mcp/repository/tree", "type": "WholePRTreeType", "digest": pr_tree["tree_digest"]},
        {"uri": "sigil://mcp/repository/statik-memory", "type": "EmbodiedSTATIKMemoryType", "checkpoint": federation["embodied_statik_memory"]["checkpoint"]},
    ]
    resources.extend(
        {
            "uri": f"sigil://mcp/kokompi/{actor.lower()}",
            "type": "KokompiAgentType",
            "actor": actor,
            "effects": ["DESCRIBE", "READ", "VALIDATE", "PLAN"],
        }
        for actor in registered
    )
    body = {
        "schema_id": "SIGILITAS_PACA_QUARTO_PANDOC_EXTERNAL_MCP_V1",
        "repository": repository,
        "head_sha": head_sha,
        "interface": "sigil://mcp/external/koko-sdk/v1",
        "registered_agent_count": len(registered),
        "registered_agents": registered,
        "resources": resources,
        "operations": ["DESCRIBE", "READ", "VALIDATE", "PLAN"],
        "editorial_factorization": editorial_receipt,
        "presentation": {
            "paca_quarto": "PACAQuartoProjectionType",
            "paca_pandoc": "PACAPandocASTProjectionType",
            "source_bound": True,
        },
        "kokompicracia": {
            "model": "KokoSDKTypedKokompicracia",
            "global_policy_precedes_agent_policy": True,
            "all_registered_agents_exposed": len(registered) == len([r for r in resources if r["type"] == "KokompiAgentType"]),
        },
        "repository_law": {
            "kind": "PARAMETRIC_TYPE_RULE",
            "rule": "RepositoryType[R] -> LiveSigilbookType[R]",
            "repository_identity_preserved": True,
            "all_github_repositories_materialized": False,
        },
        "hyperjarra_jauria": {
            "type": "HyperJarraJauriaType",
            "member_type": "LiveSigilbookType[R]",
            "members_fused": False,
            "index_is_authority": False,
        },
        "invariants": {
            "hidden_learning": False,
            "hidden_sync": False,
            "server_started": False,
            "repository_mutated": False,
            "runtime_authority": False,
        },
        "verdict": "ADMIT" if registered and pr_tree["verdict"] == "ADMIT" and federation["verdict"] == "ADMIT" and editorial_receipt["verdict"] == "ADMIT" else "HOLD",
    }
    body["exposure_digest"] = digest(body)
    return body


__all__ = ["canonical_mcp_exposure"]
