"""Video rendering script for table tennis video editing."""

import argparse
import os
import sys
import subprocess
import shutil


def parse_args():
    parser = argparse.ArgumentParser(description="Render table tennis video from events JSON")
    parser.add_argument("input_file", help="Path to input video file")
    parser.add_argument("output_file", help="Path to output video file")
    parser.add_argument("--events", required=True, help="Path to events JSON file")
    parser.add_argument("--names", default="Player 1,Player 2", help="Comma-separated player names")
    parser.add_argument(
        "--highlights-only",
        action="store_true",
        help="Export only highlighted clips (maintains accurate scoreboard)",
    )
    parser.add_argument(
        "--include-highlights",
        action="store_true",
        help="Render both full match AND highlights reel (2 output videos)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Force fresh render (delete any existing temp files)",
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Use CPU encoding (libx264) instead of hardware (VideoToolbox)",
    )
    parser.add_argument(
        "--bitrate",
        default=None,
        help="Video bitrate for hardware encoding (default: 80M for 4K, 30M for 1080p)",
    )
    return parser.parse_args()


def process_video(events, args, highlights_only=False, keep_temp=False):
    """Process events and render video with scoreboard overlays."""
    from tt_video_editor.core import get_video_properties
    from tt_video_editor.scoreboard.scoreboard_generator import ScoreboardGenerator

    if not events:
        print("No events to process.")
        return

    # Get input video properties
    input_fps, _ = get_video_properties(args.input_file)
    output_fps = str(int(input_fps)) if input_fps > 0 else "60"

    # Get input resolution
    import subprocess as sp

    try:
        result = sp.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0",
                args.input_file,
            ],
            capture_output=True,
            text=True,
        )
        # Filter out empty strings from trailing comma
        parts = [p for p in result.stdout.strip().split(",") if p]
        width, height = int(parts[0]), int(parts[1])
    except Exception:
        width, height = 1920, 1080  # fallback

    print(
        f"Rendering video at {width}x{height} @ {output_fps}fps (highlights_only={highlights_only})"
    )

    # Encoder selection
    use_cpu = getattr(args, "cpu", False)
    if use_cpu:
        encoder = "libx264"
        encoder_opts = ["-preset", "medium", "-crf", "18"]
        print("Using CPU encoder (libx264, CRF 18)")
    else:
        encoder = "h264_videotoolbox"
        # VideoToolbox uses bitrate. 80M for 4K sports, 30M for 1080p
        if args.bitrate:
            bitrate = args.bitrate
        else:
            bitrate = "80M" if width > 1920 else "30M"
        encoder_opts = ["-b:v", bitrate]
        print(f"Using hardware encoder (VideoToolbox, {bitrate})")

    # Count highlights
    if highlights_only:
        highlight_count = sum(1 for e in events if e.get("isHighlight", False))
        print(f"Found {highlight_count} highlighted clips out of {len(events)} total")
        if highlight_count == 0:
            print("No highlights found. Nothing to render.")
            return

    # Init scoring state (process ALL events for accurate scoreboard)
    game_num = 1
    p1_score = 0
    p2_score = 0
    p1_sets = 0
    p2_sets = 0
    p1_timeout_taken = False
    p2_timeout_taken = False

    temp_dir = "temp_overlays"
    clean = getattr(args, "clean", False)
    if clean and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        print("Cleaned temp directory for fresh render.")

    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    p1_name, p2_name = args.names.split(",")
    gen = ScoreboardGenerator(p1_name, p2_name, width=width, height=height)

    processed_segments = []

    # Only add game card if not highlights-only mode
    if not highlights_only:
        game_card_path = os.path.join(temp_dir, "game_1.png")
        gen.create_game_card(1, game_card_path)
        processed_segments.append(
            {
                "type": "card",
                "path": game_card_path,
                "duration": 2.0,
                "filename": "card_game_1.mp4",
            }
        )

    for i, event in enumerate(events):
        # Create overlay with CURRENT score (before this point)
        overlay_path = os.path.join(temp_dir, f"score_{i}.png")
        gen.create_scoreboard_image(
            p1_score,
            p2_score,
            p1_sets,
            p2_sets,
            overlay_path,
            p1_timeout=p1_timeout_taken,
            p2_timeout=p2_timeout_taken,
        )

        # Only add to segments if not highlights-only OR this is a highlight
        if not highlights_only or event.get("isHighlight", False):
            processed_segments.append(
                {
                    "type": "clip",
                    "start": event["start"],
                    "end": event["end"],
                    "overlay": overlay_path,
                    "filename": f"clip_event_{i}.mp4",
                }
            )

        # Update score (always, for accurate scoreboard in future clips)
        # Update score (always, for accurate scoreboard in future clips)
        winner = event.get("winner")
        point_scored = False
        if winner == p1_name:
            p1_score += 1
            point_scored = True
        elif winner == p2_name:
            p2_score += 1
            point_scored = True

        # Check for game end
        if point_scored and (p1_score >= 11 or p2_score >= 11) and abs(p1_score - p2_score) >= 2:
            if p1_score > p2_score:
                p1_sets += 1
            else:
                p2_sets += 1

            p1_score = 0
            p2_score = 0
            game_num += 1

            # Add game card only if not highlights-only
            if not highlights_only and p1_sets < 3 and p2_sets < 3 and i < len(events) - 1:
                card_path = os.path.join(temp_dir, f"game_{game_num}.png")
                gen.create_game_card(game_num, card_path)
                processed_segments.append(
                    {
                        "type": "card",
                        "path": card_path,
                        "duration": 2.0,
                        "filename": f"card_game_{game_num}.mp4",
                    }
                )

        # Track timeouts
        if event.get("timeout_player"):
            tw = event["timeout_player"]
            if tw == p1_name:
                p1_timeout_taken = True
            else:
                p2_timeout_taken = True

    print(f"Generated {len(processed_segments)} segments. Rendering with FFmpeg...")

    # Render segments (with checkpoint support)
    concat_list_path = "concat_list.txt"
    skipped = 0
    with open(concat_list_path, "w") as f:
        for idx, seg in enumerate(processed_segments):
            seg_output = os.path.join(temp_dir, seg["filename"])
            # Fallback for old style segments if not found? No, we enforce new naming.

            # Checkpoint: skip if already rendered
            if os.path.exists(seg_output) and os.path.getsize(seg_output) > 0:
                f.write(f"file '{os.path.abspath(seg_output)}'\n")
                skipped += 1
                continue

            if seg["type"] == "card":
                cmd = (
                    [
                        "ffmpeg",
                        "-y",
                        "-loop",
                        "1",
                        "-i",
                        seg["path"],
                        "-f",
                        "lavfi",
                        "-i",
                        "anullsrc=channel_layout=stereo:sample_rate=48000",
                        "-t",
                        str(seg["duration"]),
                        "-vf",
                        f"scale={width}:{height}",
                        "-c:v",
                        encoder,
                    ]
                    + encoder_opts
                    + [
                        "-color_primaries",
                        "bt2020",
                        "-color_trc",
                        "smpte2084",
                        "-colorspace",
                        "bt2020nc",
                        "-pix_fmt",
                        "yuv420p",
                        "-r",
                        output_fps,
                        "-c:a",
                        "aac",
                        "-b:a",
                        "192k",
                        "-shortest",
                        seg_output,
                    ]
                )
                print(f"  Rendering card {idx + 1}...")
                result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    print(f"  Error: {result.stderr.decode()[:100]}")

            elif seg["type"] == "clip":
                cmd = (
                    [
                        "ffmpeg",
                        "-y",
                        "-ss",
                        str(seg["start"]),
                        "-to",
                        str(seg["end"]),
                        "-i",
                        args.input_file,
                        "-i",
                        seg["overlay"],
                        "-filter_complex",
                        "[0:v][1:v]overlay=0:0[outv]",
                        "-map",
                        "[outv]",
                        "-map",
                        "0:a",
                        "-c:v",
                        encoder,
                    ]
                    + encoder_opts
                    + [
                        "-c:a",
                        "aac",
                        "-b:a",
                        "192k",
                        "-pix_fmt",
                        "yuv420p",
                        "-r",
                        output_fps,
                        seg_output,
                    ]
                )
                duration = seg["end"] - seg["start"]
                print(f"  Rendering clip {idx + 1} ({duration:.1f}s)...")
                result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    print(f"  Error: {result.stderr.decode()[:100]}")

            f.write(f"file '{os.path.abspath(seg_output)}'\n")
            print(f"Rendered segment {idx + 1}/{len(processed_segments)}")

    if skipped > 0:
        print(f"Skipped {skipped} already-rendered segments (use --clean to re-render all)")

    # Concatenate
    print("Concatenating segments...")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list_path,
            "-c",
            "copy",
            args.output_file,
        ]
    )

    print(f"Done! Saved to {args.output_file}")

    # Cleanup
    # Cleanup
    if not keep_temp:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        if os.path.exists(concat_list_path):
            os.remove(concat_list_path)
        print("Cleaned up temporary files.")
    else:
        print(f"Temporary files kept in {temp_dir} for reuse.")


def main():
    args = parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)

    if not os.path.exists(args.events):
        print(f"Error: Events file not found: {args.events}")
        sys.exit(1)

    # Load events
    from tt_video_editor.event_manager import load_events

    events = load_events(args.events)

    if not events:
        print(f"Error: No events found in {args.events}")
        sys.exit(1)

    print(f"Loaded {len(events)} events from {args.events}")

    # Check for highlights
    highlight_count = sum(1 for e in events if e.get("isHighlight", False))

    # Process and render
    if args.include_highlights:
        # Render both full match and highlights
        print("\n=== Rendering Full Match ===")
        # Keep temp for highlights pass
        process_video(events, args, highlights_only=False, keep_temp=True)

        if highlight_count > 0:
            # Create highlights output path
            base, ext = os.path.splitext(args.output_file)
            highlights_output = f"{base}_highlights{ext}"

            # Temporarily swap output path for highlights
            original_output = args.output_file
            args.output_file = highlights_output

            print(f"\n=== Rendering Highlights Reel ({highlight_count} clips) ===")
            # Pass args.clean=False implicitly by not setting it (it's in args)
            # But we must ensure the function doesn't wipe it.
            # We already modified logic: clean happens if args.clean is set.
            # We should probably force disable clean for second pass.
            args.clean = False
            process_video(events, args, highlights_only=True, keep_temp=False)

            # Restore original
            args.output_file = original_output
            print(f"\nBoth videos complete!")
            print(f"  Full match:  {original_output}")
            print(f"  Highlights:  {highlights_output}")
        else:
            print("\nNo highlights marked - skipping highlights reel.")
    else:
        process_video(events, args, highlights_only=args.highlights_only)


if __name__ == "__main__":
    main()
