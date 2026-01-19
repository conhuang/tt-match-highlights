import sys
import os

# Ensure the src directory is in sys.path when running as a script
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from tt_video_editor.core import main

if __name__ == "__main__":
    main()
