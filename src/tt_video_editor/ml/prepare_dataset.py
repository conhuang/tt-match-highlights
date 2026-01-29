"""
Data preparation script for TTNet training.

This script extracts frames from labeled table tennis videos and converts
event annotations to TTNet-compatible format for training.

Usage:
    python -m tt_video_editor.ml.prepare_dataset \
        --events-dir /path/to/events \
        --videos-dir /path/to/raw \
        --output-dir /path/to/dataset
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import cv2


def load_events(events_path: str) -> List[Dict]:
    """Load events from JSON file."""
    with open(events_path, "r") as f:
        return json.load(f)


def match_video_to_events(videos_dir: Path, events_dir: Path) -> List[Tuple[Path, Path]]:
    """Match video files to their corresponding event files."""
    pairs = []

    for event_file in events_dir.glob("*_events.json"):
        # Extract match name from event file
        # e.g., "jonsen_vs_kenny_jiang_events.json" -> "jonsen_vs_kenny_jiang"
        match_name = event_file.stem.replace("_events", "")

        # Look for corresponding video file with any extension
        for ext in [".MOV", ".mov", ".mp4", ".MP4"]:
            video_path = videos_dir / f"{match_name}{ext}"
            if video_path.exists():
                pairs.append((video_path, event_file))
                break

    return pairs


def extract_frames_for_event(
    video_path: Path,
    event: Dict,
    output_dir: Path,
    event_idx: int,
    fps: float,
    target_size: Tuple[int, int] = (320, 128),
) -> Dict:
    """Extract frames for a single event (point) with context."""
    cap = cv2.VideoCapture(str(video_path))

    start_time = event["start"]
    end_time = event["end"]

    # Add small buffer before/after
    buffer = 0.5  # seconds
    start_frame = max(0, int((start_time - buffer) * fps))
    end_frame = int((end_time + buffer) * fps)

    # Create output directory for this event
    event_dir = output_dir / f"event_{event_idx:04d}"
    event_dir.mkdir(parents=True, exist_ok=True)

    frame_paths = []
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    for frame_num in range(start_frame, end_frame):
        ret, frame = cap.read()
        if not ret:
            break

        # Resize to target size for training
        frame_resized = cv2.resize(frame, target_size)

        frame_path = event_dir / f"frame_{frame_num:06d}.jpg"
        cv2.imwrite(str(frame_path), frame_resized, [cv2.IMWRITE_JPEG_QUALITY, 90])
        frame_paths.append(str(frame_path))

    cap.release()

    # Return annotation in TTNet format
    return {
        "event_idx": event_idx,
        "video": str(video_path.name),
        "start_frame": start_frame,
        "end_frame": end_frame,
        "start_time": start_time,
        "end_time": end_time,
        "game": event.get("game", 0),
        "winner": event.get("winner"),
        "is_highlight": event.get("isHighlight", False),
        "frame_paths": frame_paths,
        "event_labels": {
            "rally_start": int(start_time * fps) - start_frame,
            "rally_end": int(end_time * fps) - start_frame,
        },
    }


def prepare_dataset(
    events_dir: str,
    videos_dir: str,
    output_dir: str,
    val_split: float = 0.15,
    target_size: Tuple[int, int] = (320, 128),
):
    """
    Prepare training dataset from events and videos.

    Args:
        events_dir: Directory containing event JSON files
        videos_dir: Directory containing raw video files
        output_dir: Output directory for processed dataset
        val_split: Fraction of matches to use for validation
        target_size: Target frame size (width, height)
    """
    events_path = Path(events_dir)
    videos_path = Path(videos_dir)
    output_path = Path(output_dir)

    output_path.mkdir(parents=True, exist_ok=True)

    pairs = match_video_to_events(videos_path, events_path)
    print(f"Found {len(pairs)} video-event pairs")

    n_val = max(1, int(len(pairs) * val_split))
    val_pairs = pairs[:n_val]
    train_pairs = pairs[n_val:]

    print(f"Train matches: {len(train_pairs)}, Val matches: {len(val_pairs)}")

    all_annotations = {"train": [], "val": []}

    for split_name, split_pairs in [("train", train_pairs), ("val", val_pairs)]:
        split_dir = output_path / split_name
        split_dir.mkdir(exist_ok=True)

        event_global_idx = 0

        for video_path, events_file in split_pairs:
            print(f"Processing {video_path.name}...")

            cap = cv2.VideoCapture(str(video_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            print(f"  Resolution: {width}x{height}, FPS: {fps:.2f}, Frames: {total_frames}")

            events = load_events(str(events_file))
            print(f"  Found {len(events)} events")

            for event in events:
                annotation = extract_frames_for_event(
                    video_path, event, split_dir, event_global_idx, fps, target_size
                )
                all_annotations[split_name].append(annotation)
                event_global_idx += 1

                if event_global_idx % 10 == 0:
                    print(f"    Processed {event_global_idx} events...")

    for split_name in ["train", "val"]:
        annotations_path = output_path / f"{split_name}_annotations.json"
        with open(annotations_path, "w") as f:
            json.dump(all_annotations[split_name], f, indent=2)
        n_ann = len(all_annotations[split_name])
        print(f"Saved {n_ann} {split_name} annotations to {annotations_path}")

    info = {
        "train_events": len(all_annotations["train"]),
        "val_events": len(all_annotations["val"]),
        "target_size": list(target_size),
        "train_matches": [str(p[0].name) for p in train_pairs],
        "val_matches": [str(p[0].name) for p in val_pairs],
    }
    with open(output_path / "dataset_info.json", "w") as f:
        json.dump(info, f, indent=2)

    print("\nDataset prepared successfully!")
    print(f"  Train: {info['train_events']} events from {len(train_pairs)} matches")
    print(f"  Val: {info['val_events']} events from {len(val_pairs)} matches")


def main():
    parser = argparse.ArgumentParser(description="Prepare dataset for TTNet training")
    parser.add_argument("--events-dir", required=True, help="Directory with event JSON files")
    parser.add_argument("--videos-dir", required=True, help="Directory with raw video files")
    parser.add_argument("--output-dir", required=True, help="Output directory for dataset")
    parser.add_argument("--val-split", type=float, default=0.15, help="Validation split ratio")
    parser.add_argument("--width", type=int, default=320, help="Target frame width")
    parser.add_argument("--height", type=int, default=128, help="Target frame height")

    args = parser.parse_args()

    prepare_dataset(
        events_dir=args.events_dir,
        videos_dir=args.videos_dir,
        output_dir=args.output_dir,
        val_split=args.val_split,
        target_size=(args.width, args.height),
    )


if __name__ == "__main__":
    main()
