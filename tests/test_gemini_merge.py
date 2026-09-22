"""
Unit tests for Gemini rally response parsing and boundary merging.
"""

import os
import sys

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from tt_video_editor.ml.gemini.detector import clean_json_response, merge_adjacent_rallies


def test_clean_json_response_with_markdown_fences():
    """Verify parsing JSON from markdown code block fences."""
    raw = """```json
    [
      {
        "start_time": 12.5,
        "end_time": 18.2,
        "point_summary": "High speed counter rally",
        "rally_shot_count": 6,
        "is_highlight": true
      }
    ]
    ```"""
    parsed = clean_json_response(raw)
    assert len(parsed) == 1
    assert parsed[0]["start_time"] == 12.5
    assert parsed[0]["end_time"] == 18.2
    assert parsed[0]["is_highlight"] is True


def test_clean_json_response_raw():
    """Verify parsing standard raw JSON."""
    raw = '[{"start_time": 5.0, "end_time": 10.0}]'
    parsed = clean_json_response(raw)
    assert len(parsed) == 1
    assert parsed[0]["start_time"] == 5.0


def test_merge_adjacent_rallies_empty():
    """Verify empty input returns empty list."""
    assert merge_adjacent_rallies([]) == []


def test_merge_adjacent_rallies_overlapping():
    """
    Verify that overlapping intervals across chunk boundaries are merged
    and highlight flags are preserved.
    """
    chunk1_rallies = [
        {"start_time": 10.0, "end_time": 16.0, "is_highlight": False, "point_summary": "Forehand topspin"},
        {"start_time": 25.0, "end_time": 30.5, "is_highlight": True, "point_summary": "Smash winner"}
    ]
    # Chunk 2 overlaps slightly or is adjacent (within max_gap=1.0s)
    chunk2_rallies = [
        {"start_time": 31.0, "end_time": 35.0, "is_highlight": False, "point_summary": "Continued reaction"},
        {"start_time": 45.0, "end_time": 50.0, "is_highlight": False, "point_summary": "Backhand push"}
    ]

    all_rallies = chunk1_rallies + chunk2_rallies
    merged = merge_adjacent_rallies(all_rallies, max_gap=1.0)

    # Intervals 25.0-30.5 and 31.0-35.0 have gap 0.5s <= 1.0s, so they should be merged!
    assert len(merged) == 3
    assert merged[0]["start_time"] == 10.0
    assert merged[0]["end_time"] == 16.0

    assert merged[1]["start_time"] == 25.0
    assert merged[1]["end_time"] == 35.0
    assert merged[1]["is_highlight"] is True
    assert merged[1]["point_summary"] == "Smash winner"

    assert merged[2]["start_time"] == 45.0
    assert merged[2]["end_time"] == 50.0


def test_merge_adjacent_rallies_disjoint():
    """Verify disjoint intervals with gap > max_gap remain distinct."""
    rallies = [
        {"start_time": 10.0, "end_time": 15.0},
        {"start_time": 18.0, "end_time": 24.0}
    ]
    merged = merge_adjacent_rallies(rallies, max_gap=1.0)
    assert len(merged) == 2
    assert merged[0]["end_time"] == 15.0
    assert merged[1]["start_time"] == 18.0
