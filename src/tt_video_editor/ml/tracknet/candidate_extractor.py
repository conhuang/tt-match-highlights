"""
TrackNet Ball Trajectory Candidate Extractor.

Processes frame-level ball coordinates from TrackNet CSV telemetry:
1. Calculates frame-to-frame velocity to eliminate stationary balls (table bounces / serve preparation).
2. Performs temporal gap dilation to bridge short occlusion intervals (paddle/player obscuring ball).
3. Evaluates minimum duration and spatial displacement to extract candidate rally intervals.
"""

import os
import csv
import math
from typing import List, Dict, Any, Optional


def extract_tracknet_candidates(
    csv_path_or_records,
    fps: float = 60.0,
    gap_sec: float = 1.5,
    min_dur_sec: float = 1.2,
    min_speed_px: float = 3.0,
    min_displacement_px: float = 30.0
) -> List[Dict[str, float]]:
    """
    Extract high-motion rally candidate intervals from TrackNet ball coordinates.

    Args:
        csv_path_or_records: Either a filepath to the TrackNet output CSV or a list of (vis, x, y) tuples.
        fps: Frames per second of the source video (default: 60.0).
        gap_sec: Maximum occlusion duration (in seconds) to bridge between detections.
        min_dur_sec: Minimum candidate rally duration in seconds.
        min_speed_px: Minimum velocity in pixels/frame required to be considered in motion.
        min_displacement_px: Minimum spatial bounding box spread across x or y to reject stationary bouncing.

    Returns:
        List of dicts: [{"start": 14.2, "end": 21.8, "duration": 7.6}, ...]
    """
    records = []

    if isinstance(csv_path_or_records, str):
        if not os.path.exists(csv_path_or_records):
            return []
        try:
            with open(csv_path_or_records, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    vis_val = 0
                    x_val = 0.0
                    y_val = 0.0

                    # Parse visibility
                    for vis_col in ["Visibility", "visibility", "vis"]:
                        if vis_col in row:
                            try:
                                vis_val = 1 if float(row[vis_col]) > 0 else 0
                                break
                            except Exception:
                                pass

                    # Parse X and Y
                    for x_col in ["X", "x"]:
                        if x_col in row:
                            try:
                                x_val = float(row[x_col])
                                break
                            except Exception:
                                pass

                    for y_col in ["Y", "y"]:
                        if y_col in row:
                            try:
                                y_val = float(row[y_col])
                                break
                            except Exception:
                                pass

                    if vis_val == 0 and x_val > 0 and y_val > 0:
                        vis_val = 1

                    records.append((vis_val, x_val, y_val))
        except Exception:
            return []
    elif isinstance(csv_path_or_records, list):
        records = csv_path_or_records
    else:
        return []

    total_frames = len(records)
    if total_frames == 0:
        return []

    # 1. Compute velocity & filter out stationary points (bouncing in place / dead ball)
    active_motion = [0] * total_frames
    for i in range(1, total_frames):
        v_prev, x_prev, y_prev = records[i - 1]
        v_cur, x_cur, y_cur = records[i]
        if v_cur == 1:
            if v_prev == 1 and x_prev > 0 and x_cur > 0:
                dist = math.hypot(x_cur - x_prev, y_cur - y_prev)
                if dist >= min_speed_px:
                    active_motion[i] = 1
            else:
                active_motion[i] = 1

    # 2. Gap dilation (bridge up to gap_sec of occlusions)
    gap_span = int(fps * gap_sec)
    buffered = [0] * total_frames
    last_seen = -999999
    for idx, val in enumerate(active_motion):
        if val == 1:
            last_seen = idx
        if (idx - last_seen) <= gap_span:
            buffered[idx] = 1

    # 3. Extract intervals with displacement checks
    min_span = int(fps * min_dur_sec)
    candidates = []
    in_potential = False
    start_frame = 0

    for f, is_active in enumerate(buffered):
        if is_active and not in_potential:
            start_frame = f
            in_potential = True
        elif not is_active and in_potential:
            if (f - start_frame) >= min_span:
                # Check overall bounding box displacement
                xs = [records[k][1] for k in range(start_frame, f) if records[k][0] == 1 and records[k][1] > 0]
                ys = [records[k][2] for k in range(start_frame, f) if records[k][0] == 1 and records[k][2] > 0]
                if xs and ys:
                    delta_x = max(xs) - min(xs)
                    delta_y = max(ys) - min(ys)
                    if delta_x >= min_displacement_px or delta_y >= min_displacement_px:
                        s_sec = round(start_frame / fps, 2)
                        e_sec = round(f / fps, 2)
                        candidates.append({
                            "start": s_sec,
                            "end": e_sec,
                            "duration": round(e_sec - s_sec, 2)
                        })
            in_potential = False

    if in_potential and (total_frames - start_frame) >= min_span:
        xs = [records[k][1] for k in range(start_frame, total_frames) if records[k][0] == 1 and records[k][1] > 0]
        ys = [records[k][2] for k in range(start_frame, total_frames) if records[k][0] == 1 and records[k][2] > 0]
        if xs and ys:
            delta_x = max(xs) - min(xs)
            delta_y = max(ys) - min(ys)
            if delta_x >= min_displacement_px or delta_y >= min_displacement_px:
                s_sec = round(start_frame / fps, 2)
                e_sec = round(total_frames / fps, 2)
                candidates.append({
                    "start": s_sec,
                    "end": e_sec,
                    "duration": round(e_sec - s_sec, 2)
                })

    return candidates
