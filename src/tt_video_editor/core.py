import argparse
import sys
import os
import subprocess
import logging
from tt_video_editor.models import Video
from tt_video_editor.event_manager import (
    load_events,
    save_events,
    get_default_event_path,
    collect_events
)
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Table Tennis Highlights Automator")
    parser.add_argument("input_file", help="Path to input video file")
    parser.add_argument("output_file", help="Path to output video file")
    parser.add_argument("--names", default="Player 1,Player 2", help="Comma-separated player names")
    parser.add_argument(
        "--load-events",
        help="Path to a JSON file of events to skip logging and go straight to video processing",
    )
    parser.add_argument(
        "--resume-events",
        help="Path to a JSON file of events to resume editing from where you left off",
    )
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
        "--no-game-cards",
        action="store_true",
        help="Do not insert 'Game X' cards between games",
    )
    return parser.parse_args()


def process_video(events, video: Video, args, highlights_only=False):
    from tt_video_editor.scoreboard.scoreboard_generator import ScoreboardGenerator

    if not events:
        return
    print(video.__class__)
    
    # Get input video properties
    output_fps = str(video.fps) if video.fps > 0 else "30"

    # Get resolution from input
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
        width, height = map(int, result.stdout.strip().rstrip(",").split(","))
    except:
        print(f"Exception checking resolution: {e}")
        width, height = 1920, 1080  # fallback

    # Detect color space from source video
    try:
        result = sp.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=color_space,color_transfer,color_primaries",
                "-of",
                "csv=p=0",
                args.input_file,
            ],
            capture_output=True,
            text=True,
        )
        parts = result.stdout.strip().rstrip(",").split(",")
        if len(parts) == 3 and parts[0] != "unknown":
            color_space, color_trc, color_primaries = parts
        else:
            color_space, color_trc, color_primaries = "bt709", "bt709", "bt709"
    except:
        color_space, color_trc, color_primaries = "bt709", "bt709", "bt709"

    print(f"Generating overlays... (output: {width}x{height} @ {output_fps}fps, color: {color_space}), (highlights_only={highlights_only})")

    # Encoder selection
    use_cpu = getattr(args, "cpu", False)
    if use_cpu:
        encoder = "libx264"
        encoder_opts = ["-preset", "medium", "-crf", "18"]
        print("Using CPU encoder (libx264, CRF 18)")
    else:
        encoder = "h264_videotoolbox"
        # VideoToolbox uses bitrate. 100M for 4K sports, 30M for 1080p
        bitrate = "100M" if width > 1920 else "30M"
        encoder_opts = ["-b:v", bitrate]
        print(f"Using hardware encoder (VideoToolbox, {bitrate})")

    if highlights_only:
        highlight_count = sum(1 for e in events if e.get("isHighlight", False))
        print(f"Found {highlight_count} highlighted clips out of {len(events)} total")
        if highlight_count == 0:
            print("No highlights found. Nothing to render.")
            return
    
    # Init Logic
    game_num = 1
    p1_score = 0
    p2_score = 0
    p1_sets = 0
    p2_sets = 0
    p1_timeout_taken = False
    p2_timeout_taken = False

    video_base = os.path.splitext(os.path.basename(args.input_file))[0]
    suffix = "_highlights" if highlights_only else ""
    temp_dir = f"temp_overlays_{video_base}{suffix}"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    p1_name, p2_name = args.names.split(",")
    gen = ScoreboardGenerator(p1_name, p2_name, width=width, height=height)

    processed_segments = []

    # Find the index of the first winning event to position the Game 1 card correctly
    first_winner_idx = -1
    for idx, e in enumerate(events):
        if e["winner"] in [p1_name, p2_name]:
            first_winner_idx = idx
            break

    for i, event in enumerate(events):
        if not highlights_only and not args.no_game_cards and i == first_winner_idx:
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

        overlay_path = os.path.join(temp_dir, f"score_{i}.png")
        if not highlights_only:
            gen.create_scoreboard_image(
                p1_score,
                p2_score,
                p1_sets,
                p2_sets,
                overlay_path,
                p1_timeout=p1_timeout_taken,
                p2_timeout=p2_timeout_taken,
            )

        if not highlights_only or event.get("isHighlight", False):
            processed_segments.append(
                {
                    "type": "clip",
                    "start": event["start"],
                    "end": event["end"],
                    "overlay": overlay_path if (first_winner_idx != -1 and i >= first_winner_idx) else None,
                    "filename": f"clip_event_{i}.mp4",
                }
            )

        if event["winner"] == p1_name:
            p1_score += 1
        elif event["winner"] == p2_name:
            p2_score += 1

        if (p1_score >= 11 or p2_score >= 11) and abs(p1_score - p2_score) >= 2:
            if p1_score > p2_score:
                p1_sets += 1
            else:
                p2_sets += 1

            p1_score = 0
            p2_score = 0
            game_num += 1

            if (
                not highlights_only
                and not args.no_game_cards
                and p1_sets < 3
                and p2_sets < 3
                and i < len(events) - 1
            ):                
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

        if event.get("timeout_player"):
            tw = event["timeout_player"]
            if tw == p1_name:
                p1_timeout_taken = True
            else:
                p2_timeout_taken = True

    print(f"Generated {len(processed_segments)} segments. Rendering with FFmpeg...")

    concat_list_path = os.path.join(temp_dir, "concat_list.txt")
    failed_segments = 0
    skipped = 0
    start_total = time.time()

    with open(concat_list_path, "w") as f:
        for idx, seg in enumerate(processed_segments):
            seg_output = os.path.join(temp_dir, seg["filename"])
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
                        color_primaries,
                        "-color_trc",
                        color_trc,
                        "-colorspace",
                        color_space,
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
                print(f"  Rendering card {idx + 1}/{len(processed_segments)}...")
                start_seg = time.time()
                result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                elapsed = time.time() - start_seg
                print(f"  Done in {elapsed:.1f}s")
                if result.returncode != 0:
                    print(f"  Error: {result.stderr.decode()[:100]}")
            
            elif seg["type"] == "clip":
                overlay = [
                        "-i",
                        seg["overlay"],
                        "-filter_complex",
                        f"[0:v][1:v]overlay=0:0,scale={width}:{height}[outv]",
                        "-map",
                        "[outv]",
                        "-map",
                        "0:a:0",
                        "-c:v",
                        encoder,
                    ] if (not highlights_only and seg.get("overlay") is not None) else [] 
                cmd = (
                    [
                        "ffmpeg",
                        "-y",
                        "-ss",
                        str(seg["start"]),
                        "-to",
                        str(seg["end"]),
                        "-i",
                        args.input_file
                    ] + overlay
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
                print(f"  Rendering clip {idx + 1}/{len(processed_segments)} ({duration:.1f}s)...")
                start_seg = time.time()
                result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                elapsed = time.time() - start_seg
                print(f"  Done in {elapsed:.1f}s")
                if result.returncode != 0:
                    print(f"  Error: {result.stderr.decode()[:100]}")

            f.write(f"file '{os.path.abspath(seg_output)}'\n")
            # print(f"Rendered segment {idx + 1}/{len(processed_segments)}")

        if skipped > 0:
            print(f"Skipped {skipped} already-rendered segments (use --clean to re-render all)")

            if result.returncode != 0 or not os.path.exists(seg_output):
                failed_segments += 1
                print(f"FAILED segment {idx + 1}/{len(processed_segments)} (type={seg['type']})")
                # Print last few lines of ffmpeg error for diagnosis
                if result.stderr:
                    err_lines = result.stderr.strip().split("\n")
                    for line in err_lines[-5:]:
                        print(f"  ffmpeg: {line}")
            else:
                f.write(f"file '{os.path.abspath(seg_output)}'\n")
                print(f"Rendered segment {idx + 1}/{len(processed_segments)}")

    if failed_segments > 0:
        print(f"WARNING: {failed_segments}/{len(processed_segments)} segments failed to render.")

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
            "-color_primaries",
            color_primaries,
            "-color_trc",
            color_trc,
            "-colorspace",
            color_space,
            args.output_file,
        ]
    )

    print(f"Done! Saved to {args.output_file}")
    total_time = time.time() - start_total
    print(f"Total render time: {total_time:.1f}s")

def main():
    args = parse_args()

    video = Video(args.input_file)
    print(f"Video detected: {video.duration:.2f}s @ {video.fps} fps")

    events = []

    if args.load_events:
        events = load_events(args.load_events)
        if not events:
            print(f"FAILED: Could not load events from {args.load_events}. Exiting.")
            sys.exit(1)
    else:
        edit_args = args
        existing_events = []
        if hasattr(args, "resume_events") and args.resume_events:
            existing_events = load_events(args.resume_events) or []
            if existing_events:
                last_end = max([e["end"] for e in existing_events])
                edit_args.start_time = last_end
                print(f"Resuming from {last_end:.1f}s with {len(existing_events)} existing events.")


        events = collect_events(video, edit_args, existing_events=existing_events)

        if events:
            default_path = get_default_event_path(args.input_file)
            save_events(events, default_path)
    

    if events:
        highlight_count = sum(1 for e in events if e.get("isHighlight", False))
        if args.include_highlights:
            print("\n=== Rendering Full Match ===")
            process_video(events, video, args)
            print(f"\n=== Rendering Highlights Reel ({highlight_count} clips) ===")
            if highlight_count > 0:
                base, ext = os.path.splitext(args.output_file)
                highlights_output = f"{base}_highlights{ext}"

                original_output = args.output_file
                args.output_file = highlights_output

                print(f"\n=== Rendering Highlights Reel ({highlight_count} clips) ===")
                
                process_video(events, video, args, highlights_only=True)
                
                print("\nBoth videos complete!")
                print(f"  Full match:  {original_output}")
                print(f"  Highlights:  {highlights_output}")
        else:
            process_video(events, video, args, highlights_only=args.highlights_only)

    else:
        print("No events recorded or loaded. Exiting.")

