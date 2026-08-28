import tempfile
import unittest
from pathlib import Path

from sigilitas.pacadex import accepted_event, build, sessions, validate_session_tree
from sigilitas.livecoded_worktree import PanicVerdict, livecode_worktree, worktree_bearer
from sigilitas.pr_tree import artifact_type, type_pr_tree
from sigilitas.repo_federation import virtual_repo_session


SHA = "a" * 40


class PacadexTests(unittest.TestCase):
    def test_main_push_is_admitted(self):
        self.assertEqual(accepted_event("push", "refs/heads/main", {})[0], True)

    def test_unmerged_pr_event_is_not_admitted(self):
        self.assertEqual(accepted_event("pull_request", "refs/pull/1/merge", {})[0], False)

    def test_session_tree_is_pi_bi_safe(self):
        nodes, bunches = sessions()
        validate_session_tree(nodes, bunches)

    def test_snapshot_is_read_only_and_source_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".github/workflows").mkdir(parents=True)
            (root / ".github/workflows/test.yml").write_text("permissions: read-all\nsteps:\n  - uses: owner/action@v1\n")
            snap = build(root, "push", "refs/heads/main", SHA, "owner/repo", {"before": "b" * 40})
            self.assertEqual(snap["verdict"], "ADMIT")
            self.assertFalse(snap["invariants"]["repository_mutated"])
            self.assertTrue(snap["rag_inspection"]["source_bound"])
            self.assertEqual(snap["rag_inspection"]["findings"][0]["code"], "ACTION_NOT_PINNED_FULL_SHA")
            kokompi_resources = [x for x in snap["mcp"]["resources"] if "/kokompi/" in x["uri"]]
            self.assertEqual(len(kokompi_resources), len(snap["session_tree"]["nodes"]))
            self.assertEqual([x["phase"] for x in snap["livecoded_worktree"]["phases"]], ["INKED", "LINKED", "KINKED", "TWINKED"])
            self.assertTrue(snap["pr_tree"]["invariants"]["all_files_typed"])
            self.assertEqual(len(snap["pr_tree"]["files"]), 1)

    def test_missing_parent_cannot_hide_beneath_admit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".github/workflows").mkdir(parents=True)
            snap = build(root, "push", "refs/heads/main", SHA, "owner/repo", {})
            self.assertEqual(snap["verdict"], "HOLD")
            self.assertEqual(snap["reason"], "LIVECODED_WORKTREE_HOLD")

    def test_pr_validation_becomes_typed_hold_panic(self):
        bearer = worktree_bearer("owner/repo", "refs/pull/1/merge", SHA, {})
        session = livecode_worktree(bearer, False, "UNACCEPTED_GITHUB_EVENT", SHA)
        self.assertEqual(session["verdict"], "HOLD")
        self.assertTrue(all(p["checkpoint_preserved"] for p in session["panics"]))
        self.assertFalse(session["invariants"]["repository_mutated"])

    def test_provenance_drift_is_typed_reject(self):
        bearer = worktree_bearer("owner/repo", "refs/heads/main", SHA, {"before": "b" * 40})
        session = livecode_worktree(bearer, True, "ACCEPTED_MAIN_COMMIT", "c" * 40)
        self.assertEqual(session["verdict"], PanicVerdict.REJECT.value)
        self.assertIn("PROVENANCE_HEAD_DRIFT", {p["code"] for p in session["panics"]})

    def test_whole_tree_has_distinct_typed_nodes_and_bounded_quanta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sigilitas").mkdir()
            (root / "tests").mkdir()
            (root / "sigilitas/carrier.py").write_text("VALUE = 1\n")
            (root / "tests/test_carrier.py").write_text("assert True\n")
            tree = type_pr_tree(root)
            self.assertEqual({x["node_type"] for x in tree["files"]}, {"SigilitasRuntimeCarrierType", "ExecutableTestWitnessType"})
            self.assertEqual(len({x["node_id"] for x in tree["files"]}), 2)
            self.assertTrue(tree["causal_projection"]["acyclic"])
            self.assertTrue(tree["causal_projection"]["single_effect"])
            self.assertLessEqual(tree["causal_projection"]["max_fan_in"], 1)

    def test_unknown_artifact_is_still_primitive_typed(self):
        self.assertEqual(artifact_type("assets/value.bin"), "PrimitiveArtifactType")

    def test_repo_session_memory_and_federation_keep_distinct_bearers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("typed\n")
            session = virtual_repo_session("owner/repo", SHA, type_pr_tree(root))
            self.assertEqual(session["verdict"], "ADMIT")
            self.assertNotEqual(
                session["virtual_session"]["bearer_id"],
                session["embodied_statik_memory"]["bearer_id"],
            )
            self.assertEqual(session["federation"]["capability_composition"], "INTERSECTION")
            self.assertFalse(session["cloud_projection"]["physical_cloud_claimed"])


if __name__ == "__main__":
    unittest.main()
