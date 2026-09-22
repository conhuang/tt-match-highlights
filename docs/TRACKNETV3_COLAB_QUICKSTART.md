# TrackNetV3 Google Colab Quickstart Guide

This document provides ready-to-copy cells for running **TrackNetV3** ball tracking, stroke analysis, and speed graph generation on Google Colab GPU for input video `/content/xdf_match.mov`.

---

## 🚀 Complete Google Colab Pipeline (`xdf_match.mov`)

### Step 0: Create Output Directory
```bash
!mkdir -p /content/output
```

---

### Step 1: Generate Table Corners Helper JSON
*In Google Colab (headless), run this Python cell to generate default table corners for `xdf_match.mov`:*

```python
import json, cv2

# Auto-detect video dimensions
cap = cv2.VideoCapture("/content/xdf_match.mov")
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
cap.release()

# Order: LF (Left Front) -> RF (Right Front) -> RB (Right Back) -> LB (Left Back)
corners = {
    "corners": [
        [int(w * 0.25), int(h * 0.75)],  # Left Front
        [int(w * 0.75), int(h * 0.75)],  # Right Front
        [int(w * 0.65), int(h * 0.45)],  # Right Back
        [int(w * 0.35), int(h * 0.45)]   # Left Back
    ]
}

helper_json_path = "/content/output/xdf_match_helper_table.json"
with open(helper_json_path, "w") as f:
    json.dump(corners, f, indent=2)

print(f"✅ Generated helper table JSON at: {helper_json_path}")
```

---

### Step 2: TrackNetV3 Predict Ball Trajectory (`predict.py`)
```bash
!python predict.py \
  --video_file /content/xdf_match.mov \
  --tracknet_file exp/TrackNet_best.pt \
  --inpaintnet_file exp/InpaintNet_best.pt \
  --save_dir /content/output \
  --large_video \
  --output_video \
  --eval_mode weight \
  --video_codec libx264
```
*Outputs:* `/content/output/xdf_match_ball.csv` and `/content/output/xdf_match_predict.mp4`

---

### Step 3: Stroke, Net Velocity, and Landing Point Analysis
```bash
!python speed_analysis/stroke_zone_analysis.py \
  --video_file /content/xdf_match.mov \
  --ball_csv /content/output/xdf_match_ball.csv \
  --save_dir /content/output \
  --helper_table_json /content/output/xdf_match_helper_table.json \
  --save_video \
  --video_codec libx264 \
  --use_height_plane_scale \
  --plane_height_cm 26 \
  --camera_focal_scale 1.0
```
*Outputs:* `/content/output/xdf_match_stroke_zone.csv`, `/content/output/landing_detail.csv`, `/content/output/zone_stats.csv`, and visualization video.

---

### Step 4: Output Speed Line Graphs
```bash
!python speed_analysis/plot_speed_bounce.py \
  --input /content/output/xdf_match_stroke_zone.csv \
  --target_mode r12

!python speed_analysis/plot_speed.py \
  --input /content/output/xdf_match_stroke_zone.csv \
  --speed net_zone_max_speed_kmh
```

---

### Step 5: Download Results to Computer
```python
from google.colab import files
import os

print("Generated output files:")
for f in os.listdir("/content/output"):
    print(" -", f)

# Download CSV stroke zone results
files.download("/content/output/xdf_match_stroke_zone.csv")
```
