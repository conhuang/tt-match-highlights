"""Event capture script for table tennis video editing."""

import argparse
import os
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="Capture table tennis events from video")
    parser.add_argument("input_file", help="Path to input video file")
    parser.add_argument("--names", default="Player 1,Player 2", help="Comma-separated player names")
    parser.add_argument("--output", help="Output JSON path (default: {video_name}_events.json)")
    parser.add_argument(
        "--mode",
        choices=["manual", "hybrid"],
        default="manual",
        help="Capture mode (default: manual)",
    )
    parser.add_argument(
        "--start-time",
        type=float,
        default=None,
        help="Start video at this timestamp in seconds",
    )
    parser.add_argument(
        "--load-events",
        help="Load existing events JSON to resume capture (starts at end of last clip)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        base = os.path.splitext(args.input_file)[0]
        output_path = f"{base}_events.json"

    # Get video info
    from tt_video_editor.core import get_video_properties

    fps, duration = get_video_properties(args.input_file)
    print(f"Video detected: {duration:.2f}s @ {fps} fps")

    # Load existing events if resuming
    existing_events = []
    if args.load_events:
        from tt_video_editor.event_manager import load_events

        existing_events = load_events(args.load_events)
        if existing_events:
            print(f"Loaded {len(existing_events)} existing events from {args.load_events}")
            # Auto-set start time to end of last clip if not specified
            if args.start_time is None:
                last_end = existing_events[-1]["end"]
                args.start_time = last_end
                print(f"Resuming from {last_end:.1f}s (end of last clip)")
        else:
            print(f"Warning: No events found in {args.load_events}")

    # Default start time to 0 if not set
    if args.start_time is None:
        args.start_time = 0

    # Run capture mode
    new_events = []
    if args.mode == "manual":
        from tt_video_editor.manual_mode import run_manual_mode

        new_events = run_manual_mode(args, existing_events=existing_events)
    elif args.mode == "hybrid":
        from tt_video_editor.hybrid_mode import run_hybrid_mode

        new_events = run_hybrid_mode(args)

    # run_manual_mode now returns ALL events (existing + new)
    # So we use new_events directly as all_events
    all_events = new_events
    new_count = len(all_events) - len(existing_events)

    # Save events
    if all_events:
        from tt_video_editor.event_manager import save_events

        save_events(all_events, output_path)
        print(f"\nEvents saved to: {output_path}")
        print(f"Total events: {len(all_events)} ({new_count} new)")
        highlights = sum(1 for e in all_events if e.get("isHighlight", False))
        if highlights:
            print(f"Highlights: {highlights}")
    else:
        print("No events recorded.")


if __name__ == "__main__":
    main()
