import time
import sys
import os

# Add main directory to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'main')))

start = time.time()
print("Starting profile...")

t0 = time.time()
import tt_automator
print(f"Importing tt_automator took: {time.time() - t0:.4f}s")

t0 = time.time()
from PIL import Image, ImageFont, ImageDraw
print(f"Importing PIL took: {time.time() - t0:.4f}s")

t0 = time.time()
from scoreboard.scoreboard_generator import ScoreboardGenerator
gen = ScoreboardGenerator("P1", "P2")
print(f"Initializing ScoreboardGenerator (font loading) took: {time.time() - t0:.4f}s")

t0 = time.time()
gen.create_scoreboard_image(0, 0, 0, 0, "profile_temp.png")
print(f"Generating image took: {time.time() - t0:.4f}s")

print(f"Total time: {time.time() - start:.4f}s")
