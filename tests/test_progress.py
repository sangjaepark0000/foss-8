import json
from pathlib import Path
import tempfile
import unittest

from foss8 import progress, weeks


class ProgressTests(unittest.TestCase):
    def test_actor_repository_and_period_records_are_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "progress.json"
            store = progress.Progress(path)
            one = progress.context({"repository": "https://github.com/one/repo", "me": "one"})
            other_user = progress.context({"repository": "https://github.com/one/repo", "me": "two"})
            other_repo = progress.context({"repository": "https://github.com/two/repo", "me": "one"})
            store.toggle(one, "9/task")
            self.assertTrue(store.done(one, "9/task"))
            self.assertFalse(store.done(other_user, "9/task"))
            self.assertFalse(store.done(other_repo, "9/task"))
            self.assertFalse(store.done(one, "10/task"))
            record = json.loads(path.read_text())["contexts"][one]["9/task"]
            self.assertEqual(record["source"], "manual")
            self.assertIn("updated_at", record)

    def test_invalid_existing_state_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "progress.json"
            path.write_text("broken json")
            store = progress.Progress(path)
            with self.assertRaises(ValueError):
                store.toggle("scope", "9/task")
            self.assertEqual(path.read_text(), "broken json")

    def test_new_marks_preserve_other_saved_marks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "progress.json"
            one, two = progress.Progress(path), progress.Progress(path)
            one.toggle("scope", "9/one")
            two.toggle("scope", "9/two")
            current = progress.Progress(path)
            self.assertTrue(current.done("scope", "9/one"))
            self.assertTrue(current.done("scope", "9/two"))

    def test_task_ids_survive_team_personalization(self):
        generic = weeks.load()
        configured = weeks.load({"name": "another-team", "members": [], "task_owners": {}})
        ids = [t["id"] for p in generic for t in p["tasks"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [t["id"] for p in configured for t in p["tasks"]])


if __name__ == "__main__":
    unittest.main()
