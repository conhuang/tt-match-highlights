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
    return parser.parse_args()


def process_video(events, args, highlights_only=False):
    """Process events and render video with scoreboard overlays."""
    from tt_video_editor.scoreboard.scoreboard_generator import ScoreboardGenerator
    from tt_video_editor.core import get_video_properties

    if not events:
        print("No events to process.")
        return

    # Get input video properties
    input_fps, _ = get_video_properties(args.input_file)

    print(f"Rendering video... (highlights_only={highlights_only})")

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
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    p1_name, p2_name = args.names.split(",")
    gen = ScoreboardGenerator(p1_name, p2_name)

    processed_segments = []

    # Only add game card if not highlights-only mode
    if not highlights_only:
        game_card_path = os.path.join(temp_dir, "game_1.png")
        gen.create_game_card(1, game_card_path)
        processed_segments.append({"type": "card", "path": game_card_path, "duration": 2.0})

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
                }
            )

        # Update score (always, for accurate scoreboard in future clips)
        if event["winner"] == p1_name:
            p1_score += 1
        else:
            p2_score += 1

        # Check for game end
        if (p1_score >= 11 or p2_score >= 11) and abs(p1_score - p2_score) >= 2:
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
                processed_segments.append({"type": "card", "path": card_path, "duration": 2.0})

        # Track timeouts
        if event.get("timeout_player"):
            tw = event["timeout_player"]
            if tw == p1_name:
                p1_timeout_taken = True
            else:
                p2_timeout_taken = True

    print(f"Generated {len(processed_segments)} segments. Rendering with FFmpeg...")

    # Render segments
    concat_list_path = "concat_list.txt"
    with open(concat_list_path, "w") as f:
        for idx, seg in enumerate(processed_segments):
            seg_output = os.path.join(temp_dir, f"seg_{idx}.mp4")

            if seg["type"] == "card":
                cmd = [
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
                    "scale=1920:1080",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-crf",
                    "23",
                    "-pix_fmt",
                    "yuv420p",
                    "-r",
                    "30",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-shortest",
                    seg_output,
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            elif seg["type"] == "clip":
                cmd = [
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
                    "[0:v]scale=1920:1080[scaled];[scaled][1:v]overlay=0:0[outv]",
                    "-map",
                    "[outv]",
                    "-map",
                    "0:a",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-crf",
                    "23",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-pix_fmt",
                    "yuv420p",
                    "-r",
                    "30",
                    seg_output,
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            f.write(f"file '{os.path.abspath(seg_output)}'\n")
            print(f"Rendered segment {idx + 1}/{len(processed_segments)}")

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
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    if os.path.exists(concat_list_path):
        os.remove(concat_list_path)


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

    # Process and render
    process_video(events, args, highlights_only=args.highlights_only)


if __name__ == "__main__":
    main()
