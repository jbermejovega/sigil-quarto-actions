"""PACA Quarto static editorial factorization carrier.

This module describes plans only. It performs no filesystem, network, Git,
renderer, or quantum-runtime effects.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any, Iterable


SCHEMA_ID = "PACA_QUARTO_EDITORIAL_FACTORIZATION_V1"


class SectionScope(StrEnum):
    LOCAL = "LOCAL"
    GLOBAL = "GLOBAL"


class POSIXEffect(StrEnum):
    OPENAT_READ = "OPENAT_READ"
    FSTATAT = "FSTATAT"
    READDIR = "READDIR"
    WRITEAT_ARTIFACT = "WRITEAT_ARTIFACT"
    RENAMEAT_ATOMIC = "RENAMEAT_ATOMIC"


class QuantumSurface(StrEnum):
    ZX = "ZX_CALCULUS"
    QUIPPER = "QUIPPER"
    OPENQASM3 = "OPENQASM_3"


class UniversalAbstractFlavor(StrEnum):
    PLURAL = "PLURAL_TYPED"
    QUNO = "QUNO_TYPED"
    SACRED = "SACRED_TYPED"
    TROPE = "TROPE_TYPED"


@dataclass(frozen=True)
class UniversalAbstractType:
    type_id: str
    flavor: UniversalAbstractFlavor
    allegoric_kernel: str
    propagation_witness: str


@dataclass(frozen=True)
class TropeType:
    trope_id: str
    fiction_source_digest: str
    persistence_checkpoint: str
    allegoric_relation_witness: str
    source_class: str = "SIGIL_FICTION"
    asserted_as_fact: bool = False
    asserted_as_theorem: bool = False


@dataclass(frozen=True)
class PrimitiveSection:
    section_id: str
    scope: SectionScope
    hyperjarra_index: str
    cochain_degree: int
    content_digest: str


@dataclass(frozen=True)
class RestrictionArrow:
    arrow_id: str
    source_section: str
    target_section: str
    incidence_witness: str
    semantic_witness: str


@dataclass(frozen=True)
class IncidenceCell:
    cell_id: str
    dimension: int
    faces: tuple[str, ...] = ()


@dataclass(frozen=True)
class EditorialQuantum:
    quantum_id: str
    effect: POSIXEffect
    predecessors: tuple[str, ...]
    section_id: str
    cochain_degree: int
    output_confined: bool = True


@dataclass(frozen=True)
class AlgebraicReindexingPort:
    port_id: str
    surface: QuantumSurface
    source_index: str
    target_hyperjarra_index: str
    domain_type: str
    codomain_type: str
    semantics_witness: str
    identity_collapsed: bool = False
    physical_equivalence_claimed: bool = False


@dataclass(frozen=True)
class PrimitiveCodicex:
    codicex_id: str
    repository: str
    head_sha: str
    sections: tuple[PrimitiveSection, ...]
    restrictions: tuple[RestrictionArrow, ...]
    incidence_cells: tuple[IncidenceCell, ...]
    editorial_dag: tuple[EditorialQuantum, ...]
    ports: tuple[AlgebraicReindexingPort, ...]
    universal_abstract_types: tuple[UniversalAbstractType, ...]
    trope_types: tuple[TropeType, ...]
    algebraic_flavors: tuple[str, ...]
    pi_fixed: bool = True
    statik_editorial_mode: bool = True
    runtime_authority: bool = False


def _digest(value: Any) -> str:
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(value)
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _duplicates(values: Iterable[str]) -> bool:
    values = tuple(values)
    return len(values) != len(set(values))


def validate_codicex(codicex: PrimitiveCodicex) -> dict[str, Any]:
    hold: list[str] = []
    reject: list[str] = []
    section_ids = {x.section_id for x in codicex.sections}
    cell_ids = {x.cell_id for x in codicex.incidence_cells}
    quantum_ids = {x.quantum_id for x in codicex.editorial_dag}

    if _duplicates(x.section_id for x in codicex.sections) or _duplicates(x.cell_id for x in codicex.incidence_cells):
        reject.append("PRIMITIVE_IDENTITY_COLLAPSE")
    if _duplicates(x.quantum_id for x in codicex.editorial_dag) or _duplicates(x.port_id for x in codicex.ports):
        reject.append("FLOW_OR_PORT_IDENTITY_COLLAPSE")
    if not codicex.pi_fixed or not codicex.statik_editorial_mode or codicex.runtime_authority:
        reject.append("RULEZERO_OR_STATIK_BOUNDARY_VIOLATION")

    for section in codicex.sections:
        if section.cochain_degree < 0 or len(section.content_digest) != 64:
            hold.append(f"SECTION_WITNESS_INCOMPLETE:{section.section_id}")
    for cell in codicex.incidence_cells:
        if cell.dimension < 0 or not set(cell.faces).issubset(cell_ids):
            hold.append(f"INCIDENCE_WITNESS_INCOMPLETE:{cell.cell_id}")
    by_section = {x.section_id: x for x in codicex.sections}
    for arrow in codicex.restrictions:
        source = by_section.get(arrow.source_section)
        target = by_section.get(arrow.target_section)
        if source is None or target is None or not arrow.incidence_witness or not arrow.semantic_witness:
            hold.append(f"RESTRICTION_WITNESS_INCOMPLETE:{arrow.arrow_id}")
        elif source.scope is SectionScope.LOCAL and target.scope is SectionScope.GLOBAL:
            reject.append(f"RESTRICTION_DIRECTION_REVERSED:{arrow.arrow_id}")

    seen: set[str] = set()
    for quantum in codicex.editorial_dag:
        if quantum.section_id not in section_ids or not set(quantum.predecessors).issubset(seen):
            reject.append(f"CAUSAL_DAG_ORDER_INVALID:{quantum.quantum_id}")
        if not quantum.output_confined:
            reject.append(f"ARTIFACT_WRITE_NOT_CONFINED:{quantum.quantum_id}")
        section = by_section.get(quantum.section_id)
        if section and quantum.cochain_degree != section.cochain_degree:
            hold.append(f"COCHAIN_ALIGNMENT_MISSING:{quantum.quantum_id}")
        seen.add(quantum.quantum_id)
    if seen != quantum_ids:
        reject.append("EDITORIAL_DAG_INCOMPLETE")

    for port in codicex.ports:
        if not port.semantics_witness:
            hold.append(f"REINDEXING_SEMANTICS_WITNESS_MISSING:{port.port_id}")
        if port.identity_collapsed or port.physical_equivalence_claimed:
            reject.append(f"REINDEXING_TRUTH_BOUNDARY_VIOLATION:{port.port_id}")

    if {x.flavor for x in codicex.universal_abstract_types} != set(UniversalAbstractFlavor):
        hold.append("UNIVERSAL_ABSTRACT_FLAVOR_FAMILY_INCOMPLETE")
    for abstract_type in codicex.universal_abstract_types:
        if not abstract_type.allegoric_kernel or not abstract_type.propagation_witness:
            hold.append(f"ALLEGORIC_PROPAGATION_WITNESS_MISSING:{abstract_type.type_id}")
    for trope in codicex.trope_types:
        if len(trope.fiction_source_digest) != 64 or not trope.persistence_checkpoint or not trope.allegoric_relation_witness:
            hold.append(f"TROPE_PERSISTENCE_WITNESS_MISSING:{trope.trope_id}")
        if trope.asserted_as_fact or trope.asserted_as_theorem or trope.source_class != "SIGIL_FICTION":
            reject.append(f"TROPE_TRUTH_BOUNDARY_VIOLATION:{trope.trope_id}")

    verdict = "REJECT" if reject else "HOLD" if hold else "ADMIT"
    body = {
        "schema_id": SCHEMA_ID,
        "verdict": verdict,
        "hold_reasons": sorted(set(hold)),
        "reject_reasons": sorted(set(reject)),
        "orders": {
            "incidence": "PARTIAL_ORDER",
            "causal": "DAG",
            "cochain": "NONNEGATIVE_DEGREE",
            "orders_identified": False,
        },
        "effects": [x.value for x in POSIXEffect],
        "forbidden_effects": ["EXEC", "NETWORK", "PUBLISH", "GIT_WRITE", "SHELL"],
        "invariants": {
            "source_bound": True,
            "local_global_sections_distinct": True,
            "semantic_hyperjarra_index_is_primitive": True,
            "adapters_are_reindexers": True,
            "universal_abstract_flavors_remain_distinct": True,
            "trope_is_persistent_typed_fiction": True,
            "fiction_is_not_fact_or_theorem": True,
            "safe_replay": True,
            "repository_mutated": False,
            "runtime_started": False,
        },
        "codicex_digest": _digest(codicex),
    }
    body["receipt_digest"] = _digest(body)
    return body


def canonical_editorial_codicex(repository: str, head_sha: str) -> tuple[PrimitiveCodicex, dict[str, Any]]:
    source_digest = _digest({"repository": repository, "head_sha": head_sha})
    sections = (
        PrimitiveSection("sigilbook", SectionScope.GLOBAL, "hyperjarra://repo/root", 0, source_digest),
        PrimitiveSection("document", SectionScope.LOCAL, "hyperjarra://repo/document", 0, source_digest),
        PrimitiveSection("quantum-example", SectionScope.LOCAL, "hyperjarra://repo/document/quantum", 1, source_digest),
    )
    codicex = PrimitiveCodicex(
        codicex_id=f"paca-quarto:{repository}:{head_sha[:12]}", repository=repository, head_sha=head_sha,
        sections=sections,
        restrictions=(
            RestrictionArrow("restrict-root-document", "sigilbook", "document", "incidence:root>document", "semantic:preserve-quno"),
            RestrictionArrow("restrict-document-quantum", "document", "quantum-example", "incidence:document>quantum", "semantic:preserve-boundary"),
        ),
        incidence_cells=(IncidenceCell("root", 0), IncidenceCell("document-cell", 1, ("root",)), IncidenceCell("quantum-cell", 2, ("document-cell",))),
        editorial_dag=(
            EditorialQuantum("stat-source", POSIXEffect.FSTATAT, (), "sigilbook", 0),
            EditorialQuantum("read-source", POSIXEffect.OPENAT_READ, ("stat-source",), "document", 0),
            EditorialQuantum("render-artifact", POSIXEffect.WRITEAT_ARTIFACT, ("read-source",), "quantum-example", 1),
            EditorialQuantum("seal-artifact", POSIXEffect.RENAMEAT_ATOMIC, ("render-artifact",), "quantum-example", 1),
        ),
        ports=tuple(
            AlgebraicReindexingPort(
                f"port-{surface.value.lower()}", surface, f"index://{surface.value.lower()}",
                "hyperjarra://repo/document/quantum", "QuantumProgramSurface", "PrimitiveTypedSection",
                f"semantic-witness:{surface.value.lower()}",
            ) for surface in QuantumSurface
        ),
        universal_abstract_types=tuple(
            UniversalAbstractType(
                f"uat-{flavor.value.lower()}", flavor, "allegory://sigil/kernel/v1",
                f"propagation-witness:{flavor.value.lower()}",
            ) for flavor in UniversalAbstractFlavor
        ),
        trope_types=(
            TropeType(
                "trope-sigil-fiction", source_digest, f"checkpoint:sha256:{source_digest}",
                "allegoric-relation:sigil-fiction-to-kernel",
            ),
        ),
        algebraic_flavors=("INCIDENCE_GEOMETRY", "TROPICAL_ALGEBRAIC_GEOMETRY", "ALGEBRAIC_TOPOLOGY", "CATEGORY"),
    )
    return codicex, validate_codicex(codicex)


__all__ = ["SCHEMA_ID", "AlgebraicReindexingPort", "EditorialQuantum", "IncidenceCell", "POSIXEffect", "PrimitiveCodicex", "PrimitiveSection", "QuantumSurface", "RestrictionArrow", "SectionScope", "TropeType", "UniversalAbstractFlavor", "UniversalAbstractType", "canonical_editorial_codicex", "validate_codicex"]
