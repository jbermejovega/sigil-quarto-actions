import tempfile
import unittest
from pathlib import Path

from sigilitas.pacadex import accepted_event, build, sessions, validate_session_tree
from sigilitas.livecoded_worktree import PanicVerdict, livecode_worktree, worktree_bearer


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


if __name__ == "__main__":
    unittest.main()
