import unittest
import os
import json
import sys

# Add src to sys.path to find the package
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from tt_video_editor.event_manager import save_events, load_events, get_default_event_path


class TestEventManager(unittest.TestCase):
    def setUp(self):
        self.test_file = "test_events_persistence.json"
        self.sample_events = [
            {"start": 1.0, "end": 3.0, "winner": "Player A", "timeout_player": None},
            {"start": 5.5, "end": 8.2, "winner": "Player B", "timeout_player": "Player A"},
        ]

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_save_and_load_events(self):
        # Save
        save_events(self.sample_events, self.test_file)
        self.assertTrue(os.path.exists(self.test_file))

        # Load
        loaded_events = load_events(self.test_file)
        self.assertEqual(len(loaded_events), 2)
        self.assertEqual(loaded_events[0]["winner"], "Player A")
        self.assertEqual(loaded_events[1]["timeout_player"], "Player A")

    def test_load_non_existent_file(self):
        result = load_events("non_existent.json")
        self.assertIsNone(result)

    def test_get_default_event_path(self):
        path = get_default_event_path("videos/my_video.mp4")
        self.assertEqual(path, "videos/my_video_events.json")


if __name__ == "__main__":
    unittest.main()
