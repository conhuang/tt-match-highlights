import time
import sys
import os

# Add src to sys.path to find the package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))


def profile_startup(input_file):
    print(f"Profiling startup for: {input_file}")
    t_start = time.time()

    t0 = time.time()
    import argparse

    print(f"{'argparse':<25} | {time.time() - t0:.4f}s")

    t0 = time.time()
    import subprocess

    print(f"{'subprocess':<25} | {time.time() - t0:.4f}s")

    t0 = time.time()
    import json

    print(f"{'json':<25} | {time.time() - t0:.4f}s")

    t0 = time.time()
    from tt_video_editor.core import get_video_properties

    print(f"{'core.get_video_props':<25} | {time.time() - t0:.4f}s")

    t0 = time.time()
    fps, duration = get_video_properties(input_file)
    print(f"{'ffprobe query':<25} | {time.time() - t0:.4f}s")

    print("-" * 40)
    print(f"{'Total Startup':<25} | {time.time() - t_start:.4f}s")


if __name__ == "__main__":
    test_file = sys.argv[1] if len(sys.argv) > 1 else "testgame1.MOV"
    profile_startup(test_file)
