from pathlib import Path
from tt_video_editor.ml.prepare_dataset import match_video_to_events

events_dir = Path("/Users/conniehuang/Desktop/wtttc_trials/events")
videos_dir = Path("/Users/conniehuang/Desktop/wtttc_trials/raw")

print(f"Checking events in: {events_dir}")
print(f"Checking videos in: {videos_dir}")

pairs = match_video_to_events(videos_dir, events_dir)

print(f"\nFound {len(pairs)} matched pairs:")
for video, event in pairs:
    print(f"  {video.name} <-> {event.name}")

# Check for unmatched events
event_files = list(events_dir.glob("*_events.json"))
matched_events = {p[1] for p in pairs}
unmatched = [e for e in event_files if e not in matched_events]

if unmatched:
    print(f"\nScanning found {len(unmatched)} UNMATCHED events:")
    for e in unmatched:
        print(f"  {e.name}")
else:
    print("\nAll event files matched to videos!")
