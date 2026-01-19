def run_manual_mode(args):
    import cv2

    print(f"Starting Manual Mode for {args.input_file}...")
    print("Controls:")
    print("  SPACE: Pause/Play")
    print("  D: Mark START of point")
    print("  LEFT/RIGHT or ,/.: Seek -/+ 1 second")
    print("  A: Point for Player 1 (ends clip)")
    print("  S: Point for Player 2 (ends clip)")
    print("  Shift+A: Timeout for Player 1")
    print("  Shift+S: Timeout for Player 2")
    print("  Z: UNDO last event")
    print("  Q: Quit")

    # Try hardware-accelerated decoding for faster 4K playback
    cap = cv2.VideoCapture(args.input_file, cv2.CAP_FFMPEG)

    # Enable hardware acceleration (works on Mac with VideoToolbox, Intel Quick Sync, etc.)
    cap.set(cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY)
    cap.set(cv2.CAP_PROP_HW_DEVICE, 0)  # Use first available HW device

    fps = cap.get(cv2.CAP_PROP_FPS)

    # Performance settings for 4K 60fps - more aggressive for smoother playback
    PREVIEW_WIDTH = 640  # Smaller preview = faster resize
    FRAME_SKIP = 4  # Show every 3rd frame = 20fps effective for 60fps source
    SEEK_SECONDS = 2

    events = []
    current_start_time = None
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

            lines = [
                (f"Time: {current_time:.1f}s | Events: {len(events)}", (255, 255, 255)),
                (
                    "CLIP: "
                    + (f"{current_start_time:.1f}s" if current_start_time is not None else "OFF"),
                    (0, 255, 255),
                ),
            ]
            draw_status_overlay(frame, lines, font_scale=0.8)

            cv2.imshow("Table Tennis Automator", frame)
            last_frame = frame

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
        # Debug
        elif key != 255:
            if key not in [ord("a"), ord("s"), ord("d"), ord("z")]:
                print(f"DEBUG: Key Pressed: {key}")

        # Logic keys
        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

        if key == ord("d"):
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

        elif key in [ord("a"), ord("s")]:
            winner = p1_name if key == ord("a") else p2_name
            end_time = current_time

            start_time = 0
            if current_start_time is None:
                print("SKIPPED: Point NOT recorded because no Start Time (D) was set.")
                continue
            else:
                start_time = current_start_time

            events.append(
                {
                    "start": start_time,
                    "end": end_time,
                    "winner": winner,
                    "timeout_player": None,
                }
            )
            print(f"EVENT RECORDED: {winner} won ({start_time:.1f}-{end_time:.1f})")
            current_start_time = None

        elif key in [ord("A"), ord("S")]:
            if not events:
                print("WARNING: Cannot call timeout before any points are recorded.")
            else:
                timeout_for = p1_name if key == ord("A") else p2_name
                events[-1]["timeout_player"] = timeout_for
                print(f"TIMEOUT RECORDED: {timeout_for} took a timeout after the last point.")

    cap.release()
    cv2.destroyAllWindows()
    return events
