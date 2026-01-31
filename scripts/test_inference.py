import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

from tt_video_editor.ml.point_detector import PointDetector

MODEL_PATH = "/Users/conniehuang/Desktop/tt_models/ttnet_best.pth"
VIDEO_PATH = "/Users/conniehuang/Desktop/tt_video_editor/tests/testgame1.MOV"

if not os.path.exists(MODEL_PATH):
    print(f"Error: Model not found at {MODEL_PATH}")
    sys.exit(1)

if not os.path.exists(VIDEO_PATH):
    print(f"Error: Video not found at {VIDEO_PATH}")
    sys.exit(1)

print(f"Loading model from {MODEL_PATH}...")
detector = PointDetector(MODEL_PATH)

print(f"Running inference on {VIDEO_PATH}...")
events = detector.predict(VIDEO_PATH)

print(f"\nFound {len(events)} events:")
for i, event in enumerate(events):
    print(
        f"  Event {i + 1}: {event['start']}s - {event['end']}s (Duration: {event['end'] - event['start']:.2f}s)"
    )

# Save to file for inspection
with open("test_inference_events.json", "w") as f:
    json.dump(events, f, indent=2)
print("\nSaved events to test_inference_events.json")
