"""
Point detector using TTNet for table tennis rally detection.

This module provides a high-level interface for detecting point boundaries
in table tennis videos using a trained TTNet model.
"""

import os
from typing import Dict, List, Optional

import numpy as np

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


def check_dependencies():
    """Check if required dependencies are installed."""
    if not TORCH_AVAILABLE:
        raise ImportError(
            "PyTorch is required for point detection. Install with: pip install torch torchvision"
        )


class PointDetector:
    """
    Detects table tennis point (rally) boundaries in videos.

    Uses TTNet model for ball detection and event spotting to identify
    when rallies start and end.

    Example:
        detector = PointDetector("path/to/model.pth")
        events = detector.predict("match.mp4")
        # events = [{"start": 16.5, "end": 22.3}, ...]
    """

    def __init__(
        self,
        model_path: str,
        device: Optional[str] = None,
        confidence_threshold: float = 0.65,  # Higher threshold since model has high baseline
        min_rally_duration: float = 1.0,
        max_gap_to_merge: float = 0.5,
    ):
        """
        Initialize the point detector.

        Args:
            model_path: Path to trained TTNet model weights
            device: Device to run inference on ('cuda', 'mps', 'cpu', or None for auto)
            confidence_threshold: Minimum confidence for event detection
            min_rally_duration: Minimum rally duration in seconds
            max_gap_to_merge: Merge detections within this gap (seconds)
        """
        check_dependencies()

        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.min_rally_duration = min_rally_duration
        self.max_gap_to_merge = max_gap_to_merge

        if device is None:
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = torch.device("mps")
            else:
                self.device = torch.device("cpu")
        else:
            self.device = torch.device(device)

        self.model = None
        self.input_size = (320, 128)
        self._load_model()

    def _load_model(self):
        """Load the trained TTNet model."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        checkpoint = torch.load(self.model_path, map_location=self.device)

        from .ttnet_model import TTNet

        self.model = TTNet(dropout_p=0.5, tasks=["event_spotting"])

        if "model_state_dict" in checkpoint:
            self.model.load_state_dict(checkpoint["model_state_dict"])
        else:
            self.model.load_state_dict(checkpoint)

        self.model.to(self.device)
        self.model.eval()
        print(f"Model loaded on {self.device}", flush=True)

    def _preprocess_frames(self, batch_windows: List[List[np.ndarray]]) -> "torch.Tensor":
        """Preprocess batch of windows."""
        import cv2

        processed_batch = []
        for window in batch_windows:
            processed_window = []
            for frame in window:
                frame = cv2.resize(frame, self.input_size)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = frame.astype(np.float32) / 255.0
                processed_window.append(np.transpose(frame, (2, 0, 1)))

            # Stack 3 frames along channel dimension -> (9, H, W)
            stacked = np.concatenate(processed_window, axis=0)
            processed_batch.append(stacked)

        batch = np.stack(processed_batch)
        return torch.from_numpy(batch).to(self.device)

    def predict(self, video_path: str, batch_size: int = 32, frame_skip: int = 2) -> List[Dict]:
        """
        Detect point boundaries in a video.

        Args:
            video_path: Path to video file
            batch_size: Number of frames to process at once
            frame_skip: Process every Nth frame (1=all, 2=half, 3=third)

        Returns:
            List of detected events with start/end times in seconds
        """
        import cv2
        from collections import deque

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        effective_frames = total_frames // frame_skip
        print(
            f"Analyzing {effective_frames} frames ({total_frames / fps:.1f}s video, skip={frame_skip})...",
            flush=True,
        )

        frame_scores = []

        window_size = 3
        window_buffer = deque(maxlen=window_size)
        batch_samples = []

        frame_idx = 0
        last_progress = -1

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1

            # Skip frames for speed
            if frame_idx % frame_skip != 0:
                continue

            window_buffer.append(frame)

            if len(window_buffer) == window_size:
                # Add copy of current window
                batch_samples.append(list(window_buffer))

                if len(batch_samples) >= batch_size:
                    scores = self._process_batch(batch_samples)
                    frame_scores.extend(scores)
                    batch_samples = []

                    # Print progress every 10%
                    progress = int(frame_idx / total_frames * 100)
                    if progress // 10 > last_progress // 10:
                        print(f"Processing: {progress}%", flush=True)
                        last_progress = progress

        if batch_samples:
            scores = self._process_batch(batch_samples)
            frame_scores.extend(scores)

        cap.release()

        # Pad initial frames that didn't form a full window
        frame_scores = [0.0] * (window_size - 1) + frame_scores

        # Adjust for frame skipping - effective fps is lower
        effective_fps = fps / frame_skip
        events = self._scores_to_events(frame_scores, effective_fps)

        # Debug: show score statistics
        import numpy as np

        scores_arr = np.array(frame_scores)
        print(
            f"Score stats: min={scores_arr.min():.3f}, max={scores_arr.max():.3f}, mean={scores_arr.mean():.3f}",
            flush=True,
        )
        print(
            f"Frames above threshold ({self.confidence_threshold}): {(scores_arr > self.confidence_threshold).sum()} / {len(scores_arr)}",
            flush=True,
        )

        return events

    def _process_batch(self, batch_windows: List[List[np.ndarray]]) -> List[float]:
        """Process a batch of windows and return event scores."""
        input_tensor = self._preprocess_frames(batch_windows)

        with torch.no_grad():
            outputs = self.model(input_tensor)

            if isinstance(outputs, dict):
                event_scores = outputs.get("events", outputs.get("event_spotting"))
            else:
                event_scores = outputs[-1] if isinstance(outputs, (list, tuple)) else outputs

            # Model outputs logits for 2 classes: [no_rally, rally]
            # Apply softmax and take probability of class 0 (no-rally)
            probs = torch.softmax(event_scores, dim=1)
            no_rally_probs = probs[:, 0]  # Take class 0 probability

            scores = no_rally_probs.cpu().numpy().tolist()

        return scores

    def _scores_to_events(self, scores: List[float], fps: float) -> List[Dict]:
        """Convert frame-level scores to event boundaries."""
        events = []

        scores = np.array(scores)
        kernel_size = int(fps * 0.3)
        if kernel_size > 1:
            kernel = np.ones(kernel_size) / kernel_size
            scores = np.convolve(scores, kernel, mode="same")

        active = scores > self.confidence_threshold

        in_rally = False
        rally_start = 0

        for i, is_active in enumerate(active):
            if is_active and not in_rally:
                rally_start = i
                in_rally = True
            elif not is_active and in_rally:
                start_time = rally_start / fps
                end_time = i / fps
                duration = end_time - start_time

                if duration >= self.min_rally_duration:
                    events.append({"start": round(start_time, 2), "end": round(end_time, 2)})
                in_rally = False

        if in_rally:
            start_time = rally_start / fps
            end_time = len(scores) / fps
            if end_time - start_time >= self.min_rally_duration:
                events.append({"start": round(start_time, 2), "end": round(end_time, 2)})

        events = self._merge_close_events(events)
        return events

    def _merge_close_events(self, events: List[Dict]) -> List[Dict]:
        """Merge events that are close together."""
        if len(events) < 2:
            return events

        merged = [events[0]]

        for event in events[1:]:
            prev = merged[-1]
            gap = event["start"] - prev["end"]

            if gap <= self.max_gap_to_merge:
                prev["end"] = event["end"]
            else:
                merged.append(event)

        return merged


def predict_points(
    video_path: str, model_path: str, output_path: Optional[str] = None
) -> List[Dict]:
    """
    Convenience function to detect points in a video.

    Args:
        video_path: Path to input video
        model_path: Path to trained model
        output_path: Optional path to save results as JSON

    Returns:
        List of detected events
    """
    import json

    detector = PointDetector(model_path)
    events = detector.predict(video_path)

    if output_path:
        with open(output_path, "w") as f:
            json.dump(events, f, indent=2)
        print(f"Saved {len(events)} events to {output_path}")

    return events
