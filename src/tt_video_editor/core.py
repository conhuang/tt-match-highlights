import argparse
import sys
import os
import subprocess
import json
import shutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Table Tennis Highlights Automator")
    parser.add_argument("input_file", help="Path to input video file")
    parser.add_argument("output_file", help="Path to output video file")
    parser.add_argument(
        "--mode", choices=["manual", "hybrid"], default="manual", help="Operation mode"
    )
    parser.add_argument("--names", default="Player 1,Player 2", help="Comma-separated player names")
    parser.add_argument(
        "--load-events",
        help="Path to a JSON file of events to skip logging and go straight to video processing",
    )
    parser.add_argument("--detect-ml", action="store_true", help="Use ML model for event detection")
    parser.add_argument("--model-path", help="Path to ML model weights")
    return parser.parse_args()


def get_video_properties(input_file):
    """Use ffprobe to get FPS and duration quickly."""
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)

    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=r_frame_rate,duration,nb_frames",
            "-of",
            "json",
            input_file,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)

        stream = data["streams"][0]
        num, den = map(float, stream["r_frame_rate"].split("/"))
        fps = num / den if den != 0 else 0

        duration = float(stream.get("duration", 0))
        if duration == 0 and "nb_frames" in stream:
            duration = int(stream["nb_frames"]) / fps

        return fps, duration
    except Exception as e:
        logger.warning(f"ffprobe failed, falling back to cv2: {e}")
        import cv2

        cap = cv2.VideoCapture(input_file)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        cap.release()
        return fps, duration


def process_video(events, args):
    from tt_video_editor.scoreboard.scoreboard_generator import ScoreboardGenerator

    if not events:
        return

    # Get input video properties
    input_fps, _ = get_video_properties(args.input_file)
    output_fps = str(int(input_fps)) if input_fps > 0 else "30"

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
        width, height = map(int, result.stdout.strip().split(","))
    except:
        width, height = 1920, 1080  # fallback

    print(f"Generating overlays... (output: {width}x{height} @ {output_fps}fps)")

    # Init Logic
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

    game_card_path = os.path.join(temp_dir, "game_1.png")
    gen.create_game_card(1, game_card_path)
    processed_segments.append({"type": "card", "path": game_card_path, "duration": 2.0})

    for i, event in enumerate(events):
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

        processed_segments.append(
            {
                "type": "clip",
                "start": event["start"],
                "end": event["end"],
                "overlay": overlay_path,
            }
        )

        if event["winner"] == p1_name:
            p1_score += 1
        else:
            p2_score += 1

        if (p1_score >= 11 or p2_score >= 11) and abs(p1_score - p2_score) >= 2:
            if p1_score > p2_score:
                p1_sets += 1
            else:
                p2_sets += 1

            p1_score = 0
            p2_score = 0
            game_num += 1

            if p1_sets < 3 and p2_sets < 3 and i < len(events) - 1:
                card_path = os.path.join(temp_dir, f"game_{game_num}.png")
                gen.create_game_card(game_num, card_path)
                processed_segments.append({"type": "card", "path": card_path, "duration": 2.0})

        if event.get("timeout_player"):
            tw = event["timeout_player"]
            if tw == p1_name:
                p1_timeout_taken = True
            else:
                p2_timeout_taken = True

    print(f"Generated {len(processed_segments)} segments. Rendering with FFmpeg...")

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
                    f"scale={width}:{height}",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "18",
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
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            elif seg["type"] == "clip":
                # Downscale to 1080p and overlay scoreboard for faster encoding
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
                    "30",  # Output at 30fps for faster encoding
                    seg_output,
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            f.write(f"file '{os.path.abspath(seg_output)}'\n")
            print(f"Rendered segment {idx + 1}/{len(processed_segments)}")

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

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    if os.path.exists(concat_list_path):
        os.remove(concat_list_path)


def create_proxy_file(input_file, proxy_path=None):
    """Create a fast-seeking proxy file for editing (720p, all-keyframe)."""
    if proxy_path is None:
        base = os.path.splitext(input_file)[0]
        proxy_path = f"{base}_proxy.mp4"

    if os.path.exists(proxy_path):
        print(f"Proxy already exists: {proxy_path}")
        return proxy_path

    print(f"Creating fast-seek proxy for editing...")
    print(f"  This may take a few minutes for long videos.")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_file,
        "-vf",
        "scale=960:-2",  # 540p width
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "28",
        "-g",
        "1",  # Every frame is a keyframe = instant seeking
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        proxy_path,
    ]

    # Run with visible progress
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print(f"Proxy created: {proxy_path}")
        return proxy_path
    else:
        print(f"Proxy creation failed, using original file")
        return None


def main():
    args = parse_args()
    from tt_video_editor.event_manager import (
        load_events,
        save_events,
        get_default_event_path,
    )

    fps, duration = get_video_properties(args.input_file)
    print(f"Video detected: {duration:.2f}s @ {fps} fps")

    # PROXY CREATION DISABLED - testing hardware acceleration
    # # Check if video is 4K/large and create proxy for faster editing
    # proxy_file = None
    # try:
    #     result = subprocess.run(
    #         [
    #             "ffprobe",
    #             "-v",
    #             "error",
    #             "-select_streams",
    #             "v:0",
    #             "-show_entries",
    #             "stream=width",
    #             "-of",
    #             "csv=p=0",
    #             args.input_file,
    #         ],
    #         capture_output=True,
    #         text=True,
    #     )
    #     width = int(result.stdout.strip().rstrip(","))
    #     if width > 1920:  # 4K or larger
    #         print(f"4K video detected ({width}px). Creating edit proxy for smooth playback...")
    #         proxy_file = create_proxy_file(args.input_file)
    # except Exception as e:
    #     print(f"Note: Proxy check skipped ({e})")

    events = []

    if args.load_events:
        events = load_events(args.load_events)
        if not events:
            print(f"FAILED: Could not load events from {args.load_events}. Exiting.")
            sys.exit(1)
    else:
        # Proxy disabled - use original file directly
        edit_args = args
        # if proxy_file:
        #     import copy
        #     edit_args = copy.copy(args)
        #     edit_args.input_file = proxy_file
        #     print(f"Using proxy for editing: {proxy_file}")

        if args.mode == "manual":
            from tt_video_editor.manual_mode import run_manual_mode

            events = run_manual_mode(edit_args)
        elif args.mode == "hybrid":
            from tt_video_editor.hybrid_mode import run_hybrid_mode

            events = run_hybrid_mode(edit_args)

        if events:
            default_path = get_default_event_path(args.input_file)
            save_events(events, default_path)

    if events:
        process_video(events, args)
    else:
        print("No events recorded or loaded. Exiting.")
