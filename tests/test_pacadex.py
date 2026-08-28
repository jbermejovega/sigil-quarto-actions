import tempfile
import unittest
from pathlib import Path

from sigilitas.pacadex import accepted_event, build, sessions, validate_session_tree


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
            snap = build(root, "push", "refs/heads/main", SHA, "owner/repo", {})
            self.assertEqual(snap["verdict"], "ADMIT")
            self.assertFalse(snap["invariants"]["repository_mutated"])
            self.assertTrue(snap["rag_inspection"]["source_bound"])
            self.assertEqual(snap["rag_inspection"]["findings"][0]["code"], "ACTION_NOT_PINNED_FULL_SHA")
            kokompi_resources = [x for x in snap["mcp"]["resources"] if "/kokompi/" in x["uri"]]
            self.assertEqual(len(kokompi_resources), len(snap["session_tree"]["nodes"]))


if __name__ == "__main__":
    unittest.main()
