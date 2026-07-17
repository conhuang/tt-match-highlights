import json
import os
import logging
from models import Video

logger = logging.getLogger(__name__)

def save_events(events, filepath):
    """
    Saves a list of event dictionaries to a JSON file.
    """
    try:
        with open(filepath, 'w') as f:
            json.dump(events, f, indent=4)
        print(f"Events saved to: {filepath}")
    except Exception as e:
        logger.error(f"Failed to save events to {filepath}: {e}")

def load_events(filepath):
    """
    Loads a list of event dictionaries from a JSON file.
    """
    if not os.path.exists(filepath):
        logger.error(f"Event file not found: {filepath}")
        return None
        
    try:
        with open(filepath, 'r') as f:
            events = json.load(f)
        print(f"Loaded {len(events)} events from: {filepath}")
        return events
    except Exception as e:
        logger.error(f"Failed to load events from {filepath}: {e}")
        return None

def get_default_event_path(input_video_path):
    """
    Generates a default JSON path based on the input video filename.
    Example: video.mp4 -> video_events.json
    """
    base = os.path.splitext(input_video_path)[0]
    return f"{base}_events.json"

def collect_events(video: Video, args, existing_events=None):
    import cv2

    print(f"Starting Manual Mode for {args.input_file}...")
    print(f"Video: {video.fps:.1f} fps, {video.duration:.1f}s duration")
    print("Controls:")
    print("  SPACE: Pause/Play")
    print("  E: Mark START of point")
    print("  LEFT/RIGHT or ,/.: Seek -/+ 2 seconds")
    print("  [/]: Seek -/+ 1 minute")
    print("  1: Point for Player 1 (ends clip)")
    print("  2: Point for Player 2 (ends clip)")
    print("  3: Record clip (NO SCORE CHANGE)")
    print("  H: Mark current/last clip as HIGHLIGHT")
    print("  Shift+1 (!): Timeout for Player 1")
    print("  Shift+2 (@): Timeout for Player 2")
    print("  Z: UNDO last event")
    print("  Q: Quit")

    # Try hardware-accelerated decoding for faster 4K playback
    cap = cv2.VideoCapture(args.input_file, cv2.CAP_FFMPEG)

    # Enable hardware acceleration (works on Mac with VideoToolbox, Intel Quick Sync, etc.)
    cap.set(cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY)
    cap.set(cv2.CAP_PROP_HW_DEVICE, 0)  # Use first available HW device

    # Seek to start time if provided
    start_time = getattr(args, "start_time", 0)
    if start_time > 0:
        cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
        print(f"Starting at {start_time:.1f}s")

    # Performance settings for preview window
    # PREVIEW_WIDTH: Width of preview window in pixels. Options:
    #   480  = Very small, fastest playback
    #   640  = Small, fast playback
    #   854  = 480p standard
    #   960  = Medium (current)
    #   1280 = 720p, slower on 4K source
    #   1920 = 1080p, slowest
    PREVIEW_WIDTH = 960

    # FRAME_SKIP: Dynamically calculated to achieve ~1.5x playback speed
    # Target: effective display rate = fps / FRAME_SKIP, played at real-time
    # For 1.5x speed: FRAME_SKIP = fps / (fps * 1.5 / waitKey_rate)
    # Since we use waitKey(1), effective rate is ~1000/frame but limited by decode speed
    #
    # Simplified approach: for 1.5x speed:
    # - 60fps video: skip every 2nd frame -> 30fps @ realtime = 2x speed (close to 1.5x)
    # - 30fps video: skip every other frame -> 15fps @ realtime = 2x (but decode is slower)
    #
    # Better approach: Calculate skip to achieve target effective FPS for smooth playback
    TARGET_PLAYBACK_SPEED = 1.5
    # For higher FPS videos, we need more frame skipping
    # For 60fps: FRAME_SKIP=2 gives 30 displayed fps at ~1.5-2x speed (good)
    # For 30fps: FRAME_SKIP=1 (no skip) gives 30 displayed fps at ~1-1.5x (good)
    if video.fps >= 50:  # 60fps video (4K typically)
        FRAME_SKIP = 3  # ~2x speed for faster review of 4K content
    else:
        FRAME_SKIP = 1  # 24fps or lower

    print(f"Playback settings: FRAME_SKIP={FRAME_SKIP} for ~{TARGET_PLAYBACK_SPEED}x speed")

    # SEEK_SECONDS: How many seconds to jump per arrow key press
    SEEK_SECONDS = 2

    events = list(existing_events) if existing_events else []
    current_start_time = None
    pending_highlight = False  # Mark next clip as highlight
    paused = False

    p1_name, p2_name = args.names.split(",")

    # Score tracking
    def compute_score(events_list):
        """Compute current score and game from events."""
        p1_score, p2_score = 0, 0
        p1_games, p2_games = 0, 0
        game_num = 1

        for e in events_list:
            if e["winner"] is None:
                continue
            if e["winner"] == p1_name:
                p1_score += 1
            else:
                p2_score += 1

            # Check game end
            if (p1_score >= 11 or p2_score >= 11) and abs(p1_score - p2_score) >= 2:
                if p1_score > p2_score:
                    p1_games += 1
                else:
                    p2_games += 1
                p1_score, p2_score = 0, 0
                game_num += 1

        return p1_score, p2_score, p1_games, p2_games, game_num

    while cap.isOpened():
        if not paused:
            # Skip frames for speed
            for _ in range(FRAME_SKIP - 1):
                cap.grab()  # Fast skip without decoding

            ret, frame = cap.read()
            if not ret:
                break

            # Aggressive downscale for smooth preview
            height, width = frame.shape[:2]
            if width > PREVIEW_WIDTH:
                scale = PREVIEW_WIDTH / width
                frame = cv2.resize(
                    frame, (PREVIEW_WIDTH, int(height * scale)), interpolation=cv2.INTER_NEAREST
                )  # Fastest resize

            current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

            from .ui_utils import draw_status_overlay

            # Compute current score
            p1_score, p2_score, p1_games, p2_games, game_num = compute_score(events)

            # Build status display
            if current_start_time is not None:
                clip_status = f"REC from {current_start_time:.1f}s"
                if pending_highlight:
                    clip_status += " ⭐"
            elif events:
                # Show where last point ended so user knows where to seek
                last_end = events[-1]["end"]
                clip_status = f"Last: {last_end:.1f}s"
            else:
                clip_status = "No events"

            lines = [
                (f"G{game_num}: {p1_score}-{p2_score} ({p1_games}-{p2_games})", (0, 255, 0)),
                (f"Time: {current_time:.1f}s | {clip_status}", (255, 255, 255)),
            ]
            # EDIT font scale here to adjust size of overlay
            draw_status_overlay(frame, lines, font_scale=0.5)

            cv2.imshow("Table Tennis Automator", frame)

        # Frame delay: use waitKey(1) of all videos - FRAME_SKIP controls playback speed
        # Decode overhead naturally limits speed for 4K, lower res is faster
        if not paused:
            frame_delay_ms = 1
        else:
            frame_delay_ms = 100
        key = cv2.waitKey(frame_delay_ms) & 0xFF

        # Keyframe-aligned seeking for faster response
        # iPhone videos typically have keyframes every ~1 second
        # Dynamically calculate based on detected FPS
        KEYFRAME_INTERVAL = int(video.fps)  # ~1 second worth of frames

        if key == ord("q"):
            break
        elif key == ord(" "):
            paused = not paused
        elif key in [81, 2, ord(",")]:  # Left Arrow or ','
            current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
            target_frame = max(0, current_frame - (SEEK_SECONDS * KEYFRAME_INTERVAL))
            target_frame = int(target_frame / KEYFRAME_INTERVAL) * KEYFRAME_INTERVAL
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        elif key in [83, 3, ord(".")]:  # Right Arrow or '.'
            current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
            target_frame = current_frame + (SEEK_SECONDS * KEYFRAME_INTERVAL)
            target_frame = int(target_frame / KEYFRAME_INTERVAL + 1) * KEYFRAME_INTERVAL
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        # 1-minute jump controls
        elif key == ord("["):  # Jump back 1 minute
            current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
            target_frame = max(0, current_frame - (60 * KEYFRAME_INTERVAL))
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        elif key == ord("]"):  # Jump forward 1 minute
            current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
            target_frame = current_frame + (60 * KEYFRAME_INTERVAL)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        elif key != 255:
            if key not in [
                ord("1"),
                ord("2"),
                ord("3"),
                ord("e"),
                ord("z"),
                ord("h"),
                ord("["),
                ord("]"),
                ord("!"),
                ord("@"),
            ]:
                print(f"DEBUG: Key Pressed: {key}")

        # Logic keys
        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

        if key == ord("e"):
            current_start_time = current_time
            print(f"Clip Start set to: {current_start_time:.2f}")

        elif key == ord("z"):
            if current_start_time is not None:
                print(f"UNDO: Cleared start time mark ({current_start_time:.2f})")
                current_start_time = None
            elif events:
                removed = events.pop()
                current_start_time = removed["start"]
                # Rewind to where last event ended (or start of removed if no more events)
                if events:
                    rewind_to = events[-1]["end"]
                else:
                    rewind_to = removed["start"]
                cap.set(cv2.CAP_PROP_POS_MSEC, rewind_to * 1000)
                print(f"UNDO: Removed last event. Rewound to {rewind_to:.1f}s")
            else:
                print("UNDO: No events to remove.")

        elif key in [ord("1"), ord("2"), ord("3")]:
            if key == ord("3"):
                winner = None
            else:
                winner = p1_name if key == ord("1") else p2_name
            end_time = current_time

            start_time = 0
            if current_start_time is None:
                print("SKIPPED: Point NOT recorded because no Start Time (E) was set.")
                continue
            else:
                start_time = current_start_time

            # Compute score BEFORE this point (for display in render)
            p1_score, p2_score, p1_games, p2_games, game_num = compute_score(events)

            events.append(
                {
                    "start": start_time,
                    "end": end_time,
                    "winner": winner,
                    "timeout_player": None,
                    "isHighlight": pending_highlight,
                    "game": game_num,
                    "score_before": f"{p1_score}-{p2_score}",
                }
            )

            # Compute score AFTER for display
            if winner:
                new_p1 = p1_score + 1 if winner == p1_name else p1_score
                new_p2 = p2_score + 1 if winner == p2_name else p2_score
                highlight_str = " ⭐" if pending_highlight else ""
                print(f"G{game_num}: {new_p1}-{new_p2} | {winner} won{highlight_str}")
            else:
                highlight_str = " ⭐" if pending_highlight else ""
                print(f"Clip recorded (No Score Change){highlight_str}")

            current_start_time = None
            pending_highlight = False  # Reset after recording

        # Shift+1 (!) and Shift+2 (@) for timeouts
        elif key in [ord("!"), ord("@")]:
            if not events:
                print("WARNING: Cannot call timeout before any points are recorded.")
            else:
                timeout_for = p1_name if key == ord("!") else p2_name
                events[-1]["timeout_player"] = timeout_for
                print(f"TIMEOUT RECORDED: {timeout_for} took a timeout after the last point.")

        # H key - toggle highlight
        elif key == ord("h"):
            if current_start_time is not None:
                # Currently in a clip - toggle pending highlight
                pending_highlight = not pending_highlight
                status = "ON ⭐" if pending_highlight else "OFF"
                print(f"HIGHLIGHT {status} for current clip")
            elif events:
                # Not in a clip - toggle highlight on last recorded event
                events[-1]["isHighlight"] = not events[-1].get("isHighlight", False)
                status = "ON ⭐" if events[-1]["isHighlight"] else "OFF"
                print(
                    f"HIGHLIGHT {status} for last event ({events[-1]['start']:.1f}-{events[-1]['end']:.1f})"
                )
            else:
                print("No clip to highlight.")

    cap.release()
    cv2.destroyAllWindows()
    return events
