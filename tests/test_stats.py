import unittest
import tempfile
import json
from pathlib import Path
from datetime import date, timedelta
from gitpilot.stats import PushTracker

class TestPushTracker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initial_pushes_today(self):
        tracker = PushTracker(self.repo_path)
        self.assertEqual(tracker.get_pushes_today(), 0)

    def test_increment_push_count(self):
        tracker = PushTracker(self.repo_path)
        c1 = tracker.increment_push_count()
        self.assertEqual(c1, 1)
        c2 = tracker.increment_push_count()
        self.assertEqual(c2, 2)
        self.assertEqual(tracker.get_pushes_today(), 2)

    def test_reset_on_new_day(self):
        tracker = PushTracker(self.repo_path)
        tracker.increment_push_count()
        
        # Manually alter stats file to yesterday's date
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        with open(tracker.stats_file, "w", encoding="utf-8") as f:
            json.dump({"date": yesterday, "pushes_today": 15}, f)

        # get_pushes_today should report 0 for today
        self.assertEqual(tracker.get_pushes_today(), 0)

        # increment_push_count should reset to 1
        new_count = tracker.increment_push_count()
        self.assertEqual(new_count, 1)
        self.assertEqual(tracker.get_pushes_today(), 1)

if __name__ == '__main__':
    unittest.main()
