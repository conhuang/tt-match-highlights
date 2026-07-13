import os
import subprocess


def extract_audio(video_path):
    audio_path = "temp_audio.wav"
    # Extract mono audio at 16khz
    cmd = ["ffmpeg", "-y", "-i", video_path, "-ac", "1", "-ar", "16000", audio_path]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return audio_path


def detect_rallies_ml(video_path, model_path):
    """
    Detect rallies using trained TTNet model.

    Args:
        video_path: Path to video file
        model_path: Path to trained model weights

    Returns:
        List of (start, end) tuples in seconds
    """
    try:
        from tt_video_editor.ml.point_detector import PointDetector
    except ImportError:
        raise ImportError(
            "ML detection requires PyTorch. Install with: pip install tt_video_editor[ml]"
        )

    detector = PointDetector(model_path)
    events = detector.predict(video_path)

    # Convert to (start, end) tuples
    return [(e["start"], e["end"]) for e in events]


def detect_rallies(audio_path, threshold_ratio=0.25, window_size=1600):
    from scipy.io import wavfile
    import numpy as np

    # Read audio
    rate, data = wavfile.read(audio_path)

    # Normalize
    data = np.abs(data)
    max_val = np.max(data)
    if max_val == 0:
        return []

    # Simple Envelope Detection (Paddle hits are short, loud spikes)
    # We smooth slightly but keep it sharp

    # Thresholding
    threshold = max_val * threshold_ratio  # Minimum volume to be a "hit"

    # Find peaks (indices where value > threshold)
    # This is rough; a dedicated onset detector is better but complex.
    # For TT, volume spikes are usually hits.

    hits = np.where(data > threshold)[0]
    hits_sec = hits / rate

    # Cluster hits into rallies
    # If hits are closer than 2.0 seconds, they are same rally
    rallies = []  # (start, end)

    if len(hits_sec) == 0:
        return []

    current_start = hits_sec[0]
    current_end = hits_sec[0]

    for h in hits_sec[1:]:
        if h - current_end < 2.0:
            current_end = h
        else:
            # End of cluster
            # valid rally must have duration > 0.5s ? or at least 2 hits?
            if current_end - current_start > 0.5:
                rallies.append((current_start, current_end))
            current_start = h
            current_end = h

    # Append last
    if current_end - current_start > 0.5:
        rallies.append((current_start, current_end))

    return rallies


def run_hybrid_mode(args, existing_events=None):
    import cv2
    import numpy as np

    audio_path = None
    rallies = []

    if hasattr(args, "detect_ml") and args.detect_ml:
        print("Using ML model for rally detection...")
        model_path = args.model_path
        if not model_path:
            # Default to best model in standard location
            model_path = os.path.expanduser("~/Desktop/tt_models/ttnet_best.pth")

        if os.path.exists(model_path):
            try:
                rallies = detect_rallies_ml(args.input_file, model_path)
            except Exception as e:
                print(f"Error during ML detection: {e}. Falling back to audio.")
                audio_path = extract_audio(args.input_file)
                rallies = detect_rallies(audio_path, threshold_ratio=0.25)
        else:
            print(f"Warning: Model not found at {model_path}. Falling back to audio detection.")
            audio_path = extract_audio(args.input_file)
            rallies = detect_rallies(audio_path, threshold_ratio=0.25)
    else:
        print("Extracting audio for rally detection...")
        audio_path = extract_audio(args.input_file)
        # Calibrated default: 0.25 (Found to be optimal for testgame1.MOV)
        rallies = detect_rallies(audio_path, threshold_ratio=0.25)

    print(f"Found {len(rallies)} potential rallies.")

    events = list(existing_events) if existing_events else []

    if events:
        last_end = max([e["end"] for e in events])
        # Filter out rallies that occur before or overlapping with our last end time
        original_count = len(rallies)
        rallies = [r for r in rallies if r[0] > last_end]
        if len(rallies) < original_count:
            print(f"Skipped {original_count - len(rallies)} rallies already covered by existing events.")

    p1_name, p2_name = args.names.split(",")

    cap = cv2.VideoCapture(args.input_file)
    fps = cap.get(cv2.CAP_PROP_FPS)

    print("Starting Review Mode...")
    print("Controls:")
    print("  SPACE/Enter: Replay Clip")
    print("  A: Player 1 Won (Accept Clip)")
    print("  S: Player 2 Won (Accept Clip)")
    print("  X: Reject/Skip Clip")
    print("  Q: Quit")

    cv2.namedWindow("Table Tennis Automator", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Table Tennis Automator", 1280, 720)

    for i, (r_start, r_end) in enumerate(rallies):
        print(f"Reviewing candidate {i + 1}/{len(rallies)} ({r_start:.1f}-{r_end:.1f})")

        # Buffer around the rally
        # Start a bit before the audio starts, end a bit after
        clip_start = max(0, r_start - 2.0)
        clip_end = r_end + 1.0

        reviewing = True

        start_frame = int(clip_start * fps)
        end_frame = int(clip_end * fps)

        reviewing = True

        while reviewing:
            # Play the clip loop
            if not cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame):
                print(f"DEBUG: Failed to seek to frame {start_frame}")

            frames_shown = 0
            while True:
                # Check if we passed the end frame
                # Note: POS_FRAMES returns the index of the next frame to be captured
                if cap.get(cv2.CAP_PROP_POS_FRAMES) >= end_frame:
                    break

                ret, frame = cap.read()
                if not ret:
                    # End of video reached
                    break

                frames_shown += 1
                # Resize
                height, width = frame.shape[:2]
                if width > 1920:
                    frame = cv2.resize(frame, (1920, int(1920 * height / width)))

                msg = f"Can {i + 1}/{len(rallies)} | A/S=Win, X=Skip"

                from tt_video_editor.ui_utils import draw_status_overlay

                draw_status_overlay(frame, [msg], font_scale=1.5)

                cv2.imshow("Table Tennis Automator", frame)

                key = cv2.waitKey(int(1000 / fps)) & 0xFF
                if key == ord("q"):
                    cap.release()
                    cv2.destroyAllWindows()
                    if audio_path and os.path.exists(audio_path):
                        os.remove(audio_path)
                    return events
                elif key == ord("a"):
                    events.append({"start": clip_start, "end": clip_end, "winner": p1_name})
                    reviewing = False
                    break
                elif key == ord("s"):
                    events.append({"start": clip_start, "end": clip_end, "winner": p2_name})
                    reviewing = False
                    break
                elif key == ord("x"):
                    reviewing = False
                    break
                elif key == ord(" ") or key == 13:  # Enter
                    break  # Replay loop

            # Safety: If clip didn't play (e.g. seek failed or short clip),
            # allow interaction to prevent infinite hang
            if reviewing and frames_shown == 0:
                # Create a black frame if we can't read video
                blank_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                cv2.putText(
                    blank_frame,
                    f"Seek Error: Frame {start_frame}",
                    (50, 300),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.5,
                    (0, 0, 255),
                    2,
                )
                cv2.putText(
                    blank_frame,
                    "Press X to Skip, Q to Quit",
                    (50, 400),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (255, 255, 255),
                    2,
                )
                cv2.imshow("Table Tennis Automator", blank_frame)

                key = cv2.waitKey(100) & 0xFF
                if key == ord("q"):
                    cap.release()
                    if audio_path and os.path.exists(audio_path):
                        os.remove(audio_path)
                    cv2.destroyAllWindows()
                    return events
                elif key == ord("x"):
                    reviewing = False
                # Add other controls if needed, largely just need to not hang

    cap.release()
    cv2.destroyAllWindows()
    if audio_path and os.path.exists(audio_path):
        os.remove(audio_path)
    return events
