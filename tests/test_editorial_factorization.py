from dataclasses import replace
import unittest

from sigilitas.editorial_factorization import (
    EditorialQuantum, POSIXEffect, SectionScope,
    canonical_editorial_codicex, validate_codicex,
)


class EditorialFactorizationTests(unittest.TestCase):
    def setUp(self):
        self.codicex, self.receipt = canonical_editorial_codicex("owner/repo", "a" * 40)

    def test_canonical_codicex_admits(self):
        self.assertEqual(self.receipt["verdict"], "ADMIT")

    def test_orders_remain_distinct(self):
        self.assertFalse(self.receipt["orders"]["orders_identified"])

    def test_quantum_ports_are_identity_preserving_reindexers(self):
        self.assertEqual(len(self.codicex.ports), 3)
        self.assertTrue(all(not p.identity_collapsed for p in self.codicex.ports))

    def test_minimal_effects_exclude_exec_network_and_git(self):
        forbidden = set(self.receipt["forbidden_effects"])
        self.assertTrue({"EXEC", "NETWORK", "GIT_WRITE"}.issubset(forbidden))

    def test_reverse_local_to_global_restriction_rejects(self):
        arrow = replace(self.codicex.restrictions[0], source_section="document", target_section="sigilbook")
        receipt = validate_codicex(replace(self.codicex, restrictions=(arrow,)))
        self.assertEqual(receipt["verdict"], "REJECT")

    def test_missing_semantics_witness_holds(self):
        port = replace(self.codicex.ports[0], semantics_witness="")
        receipt = validate_codicex(replace(self.codicex, ports=(port,) + self.codicex.ports[1:]))
        self.assertEqual(receipt["verdict"], "HOLD")

    def test_causal_cycle_rejects(self):
        first = EditorialQuantum("cycle", POSIXEffect.OPENAT_READ, ("cycle",), "sigilbook", 0)
        receipt = validate_codicex(replace(self.codicex, editorial_dag=(first,)))
        self.assertEqual(receipt["verdict"], "REJECT")

    def test_all_abstract_flavors_propagate_to_allegoric_kernel(self):
        self.assertEqual(len(self.codicex.universal_abstract_types), 4)
        self.assertTrue(all(x.propagation_witness for x in self.codicex.universal_abstract_types))

    def test_trope_is_persistent_fiction_not_fact(self):
        trope = self.codicex.trope_types[0]
        self.assertEqual(trope.source_class, "SIGIL_FICTION")
        self.assertFalse(trope.asserted_as_fact)
        self.assertTrue(trope.persistence_checkpoint.startswith("checkpoint:sha256:"))


if __name__ == "__main__":
    unittest.main()
