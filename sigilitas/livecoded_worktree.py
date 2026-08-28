"""piBI-typed livecoded worktree sessions with value-level PACA panics."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Any


SHA40 = re.compile(r"^[0-9a-f]{40}$")


def digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Phase(StrEnum):
    INKED = "INKED"
    LINKED = "LINKED"
    KINKED = "KINKED"
    TWINKED = "TWINKED"


class PanicVerdict(StrEnum):
    HOLD = "HOLD"
    REJECT = "REJECT"


@dataclass(frozen=True)
class PacaPanicTyped:
    code: str
    verdict: PanicVerdict
    phase: Phase
    evidence: str
    recoverable: bool
    checkpoint_preserved: bool = True
    repository_mutated: bool = False
    runtime_authority: bool = False


@dataclass(frozen=True)
class WorkTreeBearer:
    project_id: str
    worktree_id: str
    repository: str
    ref: str
    head_sha: str
    parent_sha: str | None
    context_id: str
    capability_scope: tuple[str, ...]


def _panic(code: str, phase: Phase, evidence: str, reject: bool = False) -> PacaPanicTyped:
    return PacaPanicTyped(
        code=code,
        verdict=PanicVerdict.REJECT if reject else PanicVerdict.HOLD,
        phase=phase,
        evidence=evidence,
        recoverable=not reject,
    )


def worktree_bearer(repository: str, ref: str, head_sha: str, payload: dict[str, Any]) -> WorkTreeBearer:
    parent = payload.get("before")
    if not isinstance(parent, str) or not SHA40.fullmatch(parent):
        parent = None
    context = digest({"repository": repository, "ref": ref, "head": head_sha})
    return WorkTreeBearer(
        project_id=f"github-project:{repository}",
        worktree_id=f"github-worktree:{repository}:{ref}",
        repository=repository,
        ref=ref,
        head_sha=head_sha,
        parent_sha=parent,
        context_id=f"ctx:{context[:24]}",
        capability_scope=("event_read", "worktree_read", "receipt_plan"),
    )


def livecode_worktree(
    bearer: WorkTreeBearer,
    event_admitted: bool,
    event_reason: str,
    provenance_head_sha: str | None = None,
) -> dict[str, Any]:
    panics: list[PacaPanicTyped] = []
    if not SHA40.fullmatch(bearer.head_sha):
        panics.append(_panic("HEAD_WITNESS_MISSING", Phase.INKED, bearer.head_sha))
    if provenance_head_sha is not None and provenance_head_sha != bearer.head_sha:
        panics.append(_panic("PROVENANCE_HEAD_DRIFT", Phase.INKED, provenance_head_sha, reject=True))
    if not event_admitted:
        panics.append(_panic("EVENT_NOT_ADMITTED", Phase.INKED, event_reason))

    source = asdict(bearer)
    ink_digest = digest({"source": source, "provenance_head": provenance_head_sha or bearer.head_sha})
    inked = {
        "phase": Phase.INKED,
        "source_digest": ink_digest,
        "provenance": {"repository": bearer.repository, "head_sha": bearer.head_sha},
        "receipt": f"ink:{ink_digest}",
    }

    edges = [
        {"source": bearer.project_id, "target": bearer.worktree_id, "type": "PROJECT_HAS_WORKTREE"},
        {"source": bearer.worktree_id, "target": "github-event", "type": "WORKTREE_EMITS_EVENT"},
        {"source": "github-event", "target": "pacadex-snapshot", "type": "EVENT_PROJECTS_PACADEX"},
    ]
    linked = {"phase": Phase.LINKED, "edges": edges, "acyclic": True, "link_digest": digest(edges)}

    transition = {
        "from_head": bearer.parent_sha,
        "to_head": bearer.head_sha,
        "transition_type": "GIT_WORKTREE_STATE_CHANGE" if bearer.parent_sha else "OBSERVED_HEAD_WITHOUT_PARENT",
        "physical_kink": False,
        "curvature_claimed": False,
    }
    if bearer.parent_sha is None:
        panics.append(_panic("PARENT_CHECKPOINT_MISSING", Phase.KINKED, "event.before unavailable"))
    kinked = {"phase": Phase.KINKED, "cell": transition, "cell_digest": digest(transition)}

    omega = digest({"ink": ink_digest, "link": linked["link_digest"], "kink": kinked["cell_digest"]})
    statik_bearer = f"statik:{bearer.context_id}"
    dynamik_bearer = f"dynamik:{bearer.context_id}"
    twinked = {
        "phase": Phase.TWINKED,
        "omega_witness": f"omega:sha256:{omega}",
        "statik": {"bearer_id": statik_bearer, "worktree": bearer.worktree_id},
        "dynamik": {"bearer_id": dynamik_bearer, "transition": kinked["cell_digest"]},
        "literal_bearer_equality": False,
    }

    nodes = [
        {"id": "ink", "phase": "INKED", "effect": "HASH", "capabilities": ["provenance_hash"], "predecessors": []},
        {"id": "link", "phase": "LINKED", "effect": "TYPE", "capabilities": ["edge_type"], "predecessors": ["ink"]},
        {"id": "kink", "phase": "KINKED", "effect": "TRANSITION", "capabilities": ["transition_cell"], "predecessors": ["link"]},
        {"id": "twink", "phase": "TWINKED", "effect": "PROJECT", "capabilities": ["twin_projection"], "predecessors": ["kink"]},
    ]
    bunches = [
        {"id": "ink-link-shared", "connective": "&", "left": ["ink"], "right": ["link"], "structural_sharing": True},
        {"id": "kink-twink-separated", "connective": "*", "left": ["kink"], "right": ["twink"], "structural_sharing": False},
    ]
    worst = PanicVerdict.REJECT if any(p.verdict is PanicVerdict.REJECT for p in panics) else PanicVerdict.HOLD if panics else None
    verdict = worst.value if worst else "ADMIT"
    body = {
        "schema_id": "SIGILITAS_LIVECODED_WORKTREE_PIBI_V1",
        "verdict": verdict,
        "bearer": source,
        "phases": [inked, linked, kinked, twinked],
        "session_tree": {"logic": "piBI", "nodes": nodes, "bunches": bunches, "max_fan_in": 1, "max_fan_out": 1},
        "panics": [{**asdict(p), "verdict": p.verdict.value, "phase": p.phase.value} for p in panics],
        "invariants": {"pi_fixed": True, "safe_replay": True, "repository_mutated": False, "runtime_authority": False},
    }
    body["receipt_digest"] = digest(body)
    return body


__all__ = ["PacaPanicTyped", "PanicVerdict", "Phase", "WorkTreeBearer", "livecode_worktree", "worktree_bearer"]
