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
        confidence_threshold: float = 0.5,
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

        self.model = TTNet(dropout_p=0.5, tasks=["ball_detection", "event_spotting"])

        if "model_state_dict" in checkpoint:
            self.model.load_state_dict(checkpoint["model_state_dict"])
        else:
            self.model.load_state_dict(checkpoint)

        self.model.to(self.device)
        self.model.eval()

    def _preprocess_frames(self, frames: np.ndarray) -> "torch.Tensor":
        """Preprocess frames for model input."""
        import cv2

        processed = []
        for frame in frames:
            frame = cv2.resize(frame, self.input_size)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = frame.astype(np.float32) / 255.0
            processed.append(frame)

        batch = np.stack(processed)
        batch = np.transpose(batch, (0, 3, 1, 2))

        return torch.from_numpy(batch).to(self.device)

    def predict(self, video_path: str, batch_size: int = 16) -> List[Dict]:
        """
        Detect point boundaries in a video.

        Args:
            video_path: Path to video file
            batch_size: Number of frames to process at once

        Returns:
            List of detected events with start/end times in seconds
        """
        import cv2

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        frame_scores = []
        frames_buffer = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frames_buffer.append(frame)

            if len(frames_buffer) >= batch_size:
                scores = self._process_batch(frames_buffer)
                frame_scores.extend(scores)
                frames_buffer = []

                if frame_idx % (batch_size * 10) == 0:
                    progress = frame_idx / total_frames * 100
                    print(f"Processing: {progress:.1f}%")

            frame_idx += 1

        if frames_buffer:
            scores = self._process_batch(frames_buffer)
            frame_scores.extend(scores)

        cap.release()

        events = self._scores_to_events(frame_scores, fps)
        return events

    def _process_batch(self, frames: List[np.ndarray]) -> List[float]:
        """Process a batch of frames and return event scores."""
        input_tensor = self._preprocess_frames(np.array(frames))

        with torch.no_grad():
            outputs = self.model(input_tensor)

            if isinstance(outputs, dict):
                event_scores = outputs.get("events", outputs.get("event_spotting"))
            else:
                event_scores = outputs[-1] if isinstance(outputs, (list, tuple)) else outputs

            if event_scores.min() < 0 or event_scores.max() > 1:
                event_scores = torch.sigmoid(event_scores)

            scores = event_scores.cpu().numpy().flatten().tolist()

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
