import unittest
import sys
import os

# Add src to sys.path to find the package
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)


class TestTableTennisRefactor(unittest.TestCase):
    def test_event_manager_import(self):
        """Verify event_manager module exists and has collect_events"""
        try:
            from tt_video_editor import event_manager

            self.assertTrue(
                hasattr(event_manager, "collect_events"),
                "event_manager missing collect_events function",
            )
        except ImportError as e:
            self.fail(f"Failed to import event_manager: {e}")

    def test_core_import(self):
        """Verify core imports correctly"""
        try:
            from tt_video_editor import core

            self.assertTrue(hasattr(core, "process_video"), "core missing process_video function")
        except ImportError as e:
            self.fail(f"Failed to import core: {e}")

    def test_dependencies(self):
        """Verify dependencies are installed"""
        try:
            import cv2
            import numpy
            import scipy
            import PIL
        except ImportError as e:
            self.fail(f"Missing dependency: {e}")


if __name__ == "__main__":
    unittest.main()
