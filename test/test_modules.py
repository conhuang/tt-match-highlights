import unittest
import sys
import os

# Add project root to sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
# Also add main for direct imports in some tests
MAIN_DIR = os.path.join(ROOT_DIR, 'main')
if MAIN_DIR not in sys.path:
    sys.path.append(MAIN_DIR)

class TestTableTennisRefactor(unittest.TestCase):
    
    def test_manual_mode_import(self):
        """Verify manual_mode module exists and has run_manual_mode"""
        try:
            import manual_mode
            self.assertTrue(hasattr(manual_mode, "run_manual_mode"), "manual_mode missing run_manual_mode function")
        except ImportError as e:
            self.fail(f"Failed to import manual_mode: {e}")

    def test_hybrid_mode_import(self):
        """Verify hybrid_mode module exists and has run_hybrid_mode"""
        try:
            import hybrid_mode
            self.assertTrue(hasattr(hybrid_mode, "run_hybrid_mode"), "hybrid_mode missing run_hybrid_mode function")
            self.assertTrue(hasattr(hybrid_mode, "extract_audio"), "hybrid_mode missing extract_audio function")
            self.assertTrue(hasattr(hybrid_mode, "detect_rallies"), "hybrid_mode missing detect_rallies function")
        except ImportError as e:
            self.fail(f"Failed to import hybrid_mode: {e}")

    def test_tt_automator_import(self):
        """Verify tt_automator imports correctly"""
        try:
            import tt_automator
            self.assertTrue(hasattr(tt_automator, "process_video"), "tt_automator missing process_video function")
        except ImportError as e:
            self.fail(f"Failed to import tt_automator: {e}")

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
