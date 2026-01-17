import time
import sys
import os

# Add main directory to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'main')))

def profile_imports():
    modules_to_test = [
        ('cv2', 'import cv2'),
        ('numpy', 'import numpy as np'),
        ('scipy.io.wavfile', 'from scipy.io import wavfile'),
        ('PIL', 'from PIL import Image, ImageDraw, ImageFont'),
        ('subprocess', 'import subprocess'),
        ('argparse', 'import argparse'),
        ('manual_mode', 'import manual_mode'),
        ('hybrid_mode', 'import hybrid_mode'),
        ('scoreboard_generator', 'from scoreboard.scoreboard_generator import ScoreboardGenerator')
    ]

    print(f"{'Module':<25} | {'Time (s)':<10}")
    print("-" * 40)
    
    total_import_time = 0
    for name, cmd in modules_to_test:
        start = time.time()
        try:
            exec(cmd)
            duration = time.time() - start
            print(f"{name:<25} | {duration:.4f}")
            total_import_time += duration
        except Exception as e:
            print(f"{name:<25} | FAILED ({e})")
            
    print("-" * 40)
    print(f"{'Total Import Time':<25} | {total_import_time:.4f}s")

if __name__ == "__main__":
    print("Python Executable:", sys.executable)
    print("CWD:", os.getcwd())
    print("\nPROFILING STARTUP...")
    t_start = time.time()
    profile_imports()
    
    t0 = time.time()
    from scoreboard.scoreboard_generator import ScoreboardGenerator
    gen = ScoreboardGenerator("P1", "P2")
    print(f"{'Font Loading':<25} | {time.time() - t0:.4f}s")
    
    print("-" * 40)
    print(f"{'Overall Startup Time':<25} | {time.time() - t_start:.4f}s")
