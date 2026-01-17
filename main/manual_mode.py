def run_manual_mode(args):
    import cv2
    import numpy as np
    print(f"Starting Manual Mode for {args.input_file}...")
    print("Controls:")
    print("  SPACE: Pause/Play")
    print("  D: Mark START of point (if --explicit-start is used)")
    print("  LEFT/RIGHT or ,/.: Seek -/+ 1 second")
    print("  A: Point for Player 1 (ends clip)")
    print("  S: Point for Player 2 (ends clip)")
    print("  Shift+A: Timeout for Player 1 (after clip)")
    print("  Shift+S: Timeout for Player 2 (after clip)")
    print("  Z: UNDO last event")
    print("  Q: Quit")
    
    cap = cv2.VideoCapture(args.input_file)
    fps = cap.get(cv2.CAP_PROP_FPS)
    delay = int(1000 / fps) if fps > 0 else 30
    
    events = [] # List of {"start": float, "end": float, "winner": str}
    current_start_time = None
    paused = False
    
    # Names
    p1_name, p2_name = args.names.split(',')
    
    while cap.isOpened():
        if not paused:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Resize for better visibility if 4k
            height, width = frame.shape[:2]
            if width > 1920:
                frame = cv2.resize(frame, (1920, int(1920 * height / width)))
                
            # Add overlay text
            current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            
            from .ui_utils import draw_status_overlay
            lines = [
                (f"Time: {current_time:.1f}s | Events: {len(events)}", (255, 255, 255)),
                ("CLIP: " + (f"{current_start_time:.1f}s" if current_start_time is not None else "OFF"), (0, 255, 255))
            ]
            draw_status_overlay(frame, lines, font_scale=1.3)
            
            cv2.imshow('Table Tennis Automator', frame)
        
        key = cv2.waitKey(delay if not paused else 100) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord(' '):
            paused = not paused
        # Seek Controls
        # Support Arrow Keys (Mac/Linux varics), and standard editor keys (comma/period)
        elif key in [81, 2, ord(',')]: # Left Arrow (81/2) or ','
            cur_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
            target_frame = max(0, cur_frame - fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
            # Force update visual
            ret, frame = cap.read()
            if ret:
                from .ui_utils import draw_status_overlay
                lines = [
                    (f"Time: {current_time:.1f}s | Events: {len(events)} (SEEK)", (255, 255, 255)),
                    ("CLIP: " + (f"{current_start_time:.1f}s" if current_start_time is not None else "OFF"), (0, 255, 255))
                ]
                draw_status_overlay(frame, lines, font_scale=1.3)
            
            cv2.imshow('Table Tennis Automator', frame)

        elif key in [83, 3, ord('.')]: # Right Arrow (83/3) or '.'
             cur_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
             target_frame = min(cap.get(cv2.CAP_PROP_FRAME_COUNT), cur_frame + fps)
             cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

             # Force update visual
             ret, frame = cap.read()
             if ret:
                 from main.ui_utils import draw_status_overlay
                 lines = [
                     (f"Time: {current_time:.1f}s | Events: {len(events)} (SEEK)", (255, 255, 255)),
                     ("CLIP: " + (f"{current_start_time:.1f}s" if current_start_time is not None else "OFF"), (0, 255, 255))
                 ]
                 draw_status_overlay(frame, lines, font_scale=1.3)
                 cv2.imshow('Table Tennis Automator', frame)
        
        # Debug: Print key code if not recognized/handled above for debugging
        elif key != 255: 
             # Only print if not one of our control keys
             if key not in [ord('a'), ord('s'), ord('d'), ord('z')]:
                 print(f"DEBUG: Key Pressed: {key}") 

        # Logic keys
        current_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        
        if key == ord('d') and args.explicit_start:
            current_start_time = current_time
            print(f"Clip Start set to: {current_start_time:.2f}")
            
        elif key == ord('z'):
            if current_start_time is not None:
                print(f"UNDO: Cleared start time mark ({current_start_time:.2f})")
                current_start_time = None
            elif events:
                removed = events.pop()
                current_start_time = removed['start']
                print(f"UNDO: Removed last event. Restored start time to {current_start_time:.1f}s")
            else:
                print("UNDO: No events to remove.")
                
        elif key in [ord('a'), ord('s')]:
            winner = p1_name if key == ord('a') else p2_name
            end_time = current_time
            
            start_time = 0
            if args.explicit_start:
                if current_start_time is None:
                    print("SKIPPED: Point NOT recorded because no Start Time (D) was set.")
                    continue
                else:
                    start_time = current_start_time
            else:
                # Implicit mode: Default to 8 seconds before point ends (adjustable)
                start_time = max(0, end_time - 8)
            
            events.append({
                "start": start_time,
                "end": end_time,
                "winner": winner,
                "timeout_player": None # New field
            })
            print(f"EVENT RECORDED: {winner} won ({start_time:.1f}-{end_time:.1f})")
            
            # Reset start time
            current_start_time = None
            
        elif key in [ord('A'), ord('S')]: # Shift + A or Shift + S
            if not events:
                print("WARNING: Cannot call timeout before any points are recorded.")
            else:
                timeout_for = p1_name if key == ord('A') else p2_name
                # Attach to the LAST event
                events[-1]["timeout_player"] = timeout_for
                print(f"TIMEOUT RECORDED: {timeout_for} took a timeout after the last point.")
            
    cap.release()
    cv2.destroyAllWindows()
    return events
