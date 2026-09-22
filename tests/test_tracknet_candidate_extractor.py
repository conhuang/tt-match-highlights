"""
Unit tests for TrackNet candidate extractor.
"""

import os
import sys
import tempfile
import csv

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from tt_video_editor.ml.tracknet.candidate_extractor import extract_tracknet_candidates


def test_extract_candidates_empty():
    """Verify empty input returns empty list."""
    assert extract_tracknet_candidates([]) == []
    assert extract_tracknet_candidates("/nonexistent/path/ball.csv") == []


def test_extract_candidates_active_rally():
    """
    Simulate an active 4-second rally at 60fps (240 frames).
    Ball moves from left to right (X: 100 -> 900, Y: 300 -> 500) at high speed.
    """
    fps = 60.0
    total_frames = 240
    records = []

    for i in range(total_frames):
        # Ball moves 3.3 px/frame horizontally
        x = 100.0 + (i * 3.3)
        y = 300.0 + (i % 20) * 10
        records.append((1, x, y))

    candidates = extract_tracknet_candidates(
        records,
        fps=fps,
        gap_sec=1.0,
        min_dur_sec=1.5,
        min_speed_px=3.0,
        min_displacement_px=30.0
    )

    assert len(candidates) == 1
    assert candidates[0]["start"] <= 0.05
    assert candidates[0]["end"] == round(total_frames / fps, 2)
    assert candidates[0]["duration"] >= 3.9


def test_stationary_ball_rejected():
    """
    Simulate a player bouncing a ball in place on the table (serve prep).
    Ball moves vertically only by 5-10px and stays at X: 500.
    Should be rejected by velocity and displacement filters.
    """
    fps = 60.0
    total_frames = 180
    records = []

    for i in range(total_frames):
        # Tiny stationary bounce in place
        x = 500.0 + (i % 2) * 0.5
        y = 400.0 + (i % 5) * 1.0
        records.append((1, x, y))

    candidates = extract_tracknet_candidates(
        records,
        fps=fps,
        gap_sec=1.0,
        min_dur_sec=1.2,
        min_speed_px=3.0,
        min_displacement_px=30.0
    )

    assert len(candidates) == 0


def test_gap_dilation_bridges_occlusions():
    """
    Simulate a rally where the ball is occluded for 0.5s (30 frames) in the middle.
    Gap dilation (gap_sec=1.5) should bridge the two halves into a single candidate rally.
    """
    fps = 60.0
    records = []

    # First half: 1.5s active motion (90 frames)
    for i in range(90):
        records.append((1, 100.0 + i * 4.0, 300.0))

    # Middle occlusion: 0.5s invisible (30 frames)
    for i in range(30):
        records.append((0, 0.0, 0.0))

    # Second half: 1.5s active motion (90 frames)
    for i in range(90):
        records.append((1, 500.0 + i * 4.0, 300.0))

    candidates = extract_tracknet_candidates(
        records,
        fps=fps,
        gap_sec=1.0,  # 1.0s gap threshold > 0.5s occlusion
        min_dur_sec=1.5,
        min_speed_px=3.0,
        min_displacement_px=30.0
    )

    assert len(candidates) == 1
    # Total duration should encompass the full ~3.5s sequence
    assert candidates[0]["duration"] >= 3.4


def test_csv_file_reading():
    """Verify parsing from a physical CSV file."""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as f:
        writer = csv.writer(f)
        writer.writerow(["Frame", "Visibility", "X", "Y"])
        for i in range(120):
            writer.writerow([i, 1, 100.0 + i * 5.0, 350.0])
        csv_path = f.name

    try:
        candidates = extract_tracknet_candidates(csv_path, fps=60.0, min_dur_sec=1.0)
        assert len(candidates) == 1
        assert candidates[0]["duration"] >= 1.9
    finally:
        if os.path.exists(csv_path):
            os.remove(csv_path)
