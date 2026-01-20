def run_manual_mode(args):
    import cv2

    print(f"Starting Manual Mode for {args.input_file}...")
    print("Controls:")
    print("  SPACE: Pause/Play")
    print("  R: Mark START of point")
    print("  LEFT/RIGHT or ,/.: Seek -/+ 2 seconds")
    print("  [/]: Seek -/+ 1 minute")
    print("  1: Point for Player 1 (ends clip)")
    print("  2: Point for Player 2 (ends clip)")
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

    # FRAME_SKIP: Show every Nth frame (higher = faster, choppier)
    #   2 = 30fps effective from 60fps source
    #   3 = 20fps effective
    #   4 = 15fps effective (current)
    FRAME_SKIP = 4

    # SEEK_SECONDS: How many seconds to jump per arrow key press
    SEEK_SECONDS = 2

    events = []
    current_start_time = None
    pending_highlight = False  # Mark next clip as highlight
    paused = False

    p1_name, p2_name = args.names.split(",")

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

            # Build status display
            clip_status = "OFF"
            if current_start_time is not None:
                clip_status = f"{current_start_time:.1f}s"
                if pending_highlight:
                    clip_status += " ⭐"

            lines = [
                (f"Time: {current_time:.1f}s | Events: {len(events)}", (255, 255, 255)),
                (f"CLIP: {clip_status}", (0, 255, 255)),
            ]
            # EDIT font scale here to adjust size of overlay
            draw_status_overlay(frame, lines, font_scale=0.5)

            cv2.imshow("Table Tennis Automator", frame)

        key = cv2.waitKey(1 if not paused else 100) & 0xFF

        # Keyframe-aligned seeking for faster response
        # iPhone videos typically have keyframes every 60 frames (1 sec at 60fps)
        KEYFRAME_INTERVAL = 60

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
        # Debug
        elif key != 255:
            if key not in [
                ord("1"),
                ord("2"),
                ord("r"),
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

        if key == ord("r"):
            current_start_time = current_time
            print(f"Clip Start set to: {current_start_time:.2f}")

        elif key == ord("z"):
            if current_start_time is not None:
                print(f"UNDO: Cleared start time mark ({current_start_time:.2f})")
                current_start_time = None
            elif events:
                removed = events.pop()
                current_start_time = removed["start"]
                print(f"UNDO: Removed last event. Restored start time to {current_start_time:.1f}s")
            else:
                print("UNDO: No events to remove.")

        elif key in [ord("1"), ord("2")]:
            winner = p1_name if key == ord("1") else p2_name
            end_time = current_time

            start_time = 0
            if current_start_time is None:
                print("SKIPPED: Point NOT recorded because no Start Time (R) was set.")
                continue
            else:
                start_time = current_start_time

            events.append(
                {
                    "start": start_time,
                    "end": end_time,
                    "winner": winner,
                    "timeout_player": None,
                    "isHighlight": pending_highlight,
                }
            )
            highlight_str = " ⭐ HIGHLIGHT" if pending_highlight else ""
            print(f"EVENT RECORDED: {winner} won ({start_time:.1f}-{end_time:.1f}){highlight_str}")
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
