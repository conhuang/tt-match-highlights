#!/usr/bin/env python3
"""
Standalone CLI Harness for AI Table Tennis Rally Detection Pipeline.

Runs the complete 4-stage pipeline:
1. 720p hardware-accelerated downscaling
2. TrackNet high-speed ball motion candidate extraction
3. Chunked Gemini multimodal rally boundary verification
4. Output JSON generation with rally timestamps, shot counts, and highlight markers

Usage:
    export GEMINI_API_KEY="your-api-key"

    # Fast run with existing ball CSV:
    python scripts/detect_rallies_cli.py --video test_match.mp4 --csv test_match_ball.csv

    # Or with existing Gemini Files API handle:
    python scripts/detect_rallies_cli.py --file_handle files/wze7ikjw69fn --csv test_match_ball.csv
"""

import sys
import os
import argparse
import time

# Ensure project root is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_dir = os.path.join(root_dir, "src")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from tt_video_editor.ml.pipeline import run_ai_rally_pipeline


def print_progress(percent: int, stage: str):
    bar_length = 30
    filled = int(bar_length * (percent / 100))
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\r[{bar}] {percent:3d}% | {stage}", end="", flush=True)
    if percent >= 100:
        print()


def main():
    parser = argparse.ArgumentParser(
        description="AI Table Tennis Rally Detector CLI (TrackNet CV + Gemini Multimodal)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--video", "-v", default=None, help="Path to input video file")
    parser.add_argument("--csv", "-c", default=None, help="Path to pre-computed TrackNet ball CSV")
    parser.add_argument("--file_handle", "-f", default=None, help="Existing Google Files API handle (e.g. files/xxx)")
    parser.add_argument("--model", "-m", default="gemini-2.5-flash", help="Gemini model to query")
    parser.add_argument("--chunk_size", "-s", type=float, default=300.0, help="Temporal chunk size in seconds")
    parser.add_argument("--output_dir", "-o", default="output/ai_rallies", help="Directory to save output files")
    parser.add_argument("--tracknet_weights", default=None, help="Path to TrackNet_best.pt")
    parser.add_argument("--inpaintnet_weights", default=None, help="Path to InpaintNet_best.pt")
    args = parser.parse_args()

    if not args.video and not args.file_handle:
        parser.print_help()
        print("\nError: Please provide --video <path> or --file_handle <files/...>")
        sys.exit(1)

    print("=" * 80)
    print("🏓 Table Tennis AI Rally Detector (TrackNet + Gemini Multimodal)")
    print("=" * 80)

    start_time = time.time()
    try:
        results = run_ai_rally_pipeline(
            video_path=args.video,
            output_dir=args.output_dir,
            ball_csv_path=args.csv,
            tracknet_file=args.tracknet_weights,
            inpaintnet_file=args.inpaintnet_weights,
            gemini_model=args.model,
            file_handle=args.file_handle,
            chunk_size=args.chunk_size,
            progress_callback=print_progress
        )
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    total_time = time.time() - start_time
    rallies = results["rallies"]

    print("\n" + "=" * 80)
    print(f"🎉 Detection Complete in {total_time:.1f}s! Found {len(rallies)} total rally intervals.")
    print(f"Saved results to: {results['output_json_path']}")
    print("=" * 80)
    print(f"{'#':<3} | {'Rally Interval':<20} | {'Shots':<5} | {'Summary'}")
    print("-" * 80)
    for i, r in enumerate(rallies, 1):
        s = r["start"]
        e = r["end"]
        dur = e - s
        shots = r.get("shot_count", 0)
        summary = r.get("summary", "")
        hl = " [★ HIGHLIGHT]" if r.get("isHighlight") else ""
        print(f"{i:<3} | {s:6.1f}s - {e:6.1f}s ({dur:4.1f}s) | {shots:<5} | {summary[:38]}{hl}")
    print("-" * 80)


if __name__ == "__main__":
    main()
