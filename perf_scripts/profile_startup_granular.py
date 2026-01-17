import time
import sys
import os

# Add main directory to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'main')))

def profile_startup(input_file):
    print(f"Profiling startup for: {input_file}")
    t_start = time.time()
    
    # 1. Imports
    t0 = time.time()
    import cv2
    import numpy as np
    import argparse
    print(f"{'Basic Imports':<25} | {time.time() - t0:.4f}s")
    
    # 2. Argument Parsing (simulated)
    t0 = time.time()
    # (Fast)
    print(f"{'Argparse':<25} | {time.time() - t0:.4f}s")
    
    # 3. get_video_properties
    t0 = time.time()
    cap = cv2.VideoCapture(input_file)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0
    cap.release()
    print(f"{'Metadata (OpenCV)':<25} | {time.time() - t0:.4f}s")
    
    # 4. Mode Selection & Mode Import
    t0 = time.time()
    from manual_mode import run_manual_mode
    print(f"{'Import manual_mode':<25} | {time.time() - t0:.4f}s")
    
    # 5. First Video Capture Open (for UI)
    t0 = time.time()
    cap = cv2.VideoCapture(input_file)
    ret, frame = cap.read()
    cap.release()
    print(f"{'Initial Frame Read':<25} | {time.time() - t0:.4f}s")
    
    print("-" * 40)
    print(f"{'Overall Startup Latency':<25} | {time.time() - t_start:.4f}s")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python profile_startup.py <video_path>")
        sys.exit(1)
    profile_startup(sys.argv[1])
