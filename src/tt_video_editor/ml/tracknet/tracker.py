"""
TrackNet Batch Inference Engine for Table Tennis Ball Tracking.

Self-contained module ported from TrackNetV3_TableTennis/predict.py.
Runs TrackNet + InpaintNet inference on a 720p video and outputs a ball CSV.

Key features:
- Large-video streaming mode (Video_IterableDataset) for memory-efficient processing
- Temporal weighted ensemble for higher accuracy (eval_mode='weight')
- InpaintNet trajectory inpainting for occluded ball positions
- Stale ball detection and blanking to prevent false positives
- Progress callback for pipeline integration
"""

import os
import csv
import math
import logging
from typing import Optional, Callable, Dict, List, Any, Tuple
from collections import deque, defaultdict
from contextlib import contextmanager

import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, IterableDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from .model import TrackNet, InpaintNet

logger = logging.getLogger("ml.tracknet.tracker")

# ─────────────────────────────────────────────────────────────────────────────
# Constants (must match the model's training resolution)
# ─────────────────────────────────────────────────────────────────────────────
HEIGHT = 288
WIDTH = 512
SIGMA = 2.5
DELTA_T = 1 / math.sqrt(HEIGHT ** 2 + WIDTH ** 2)
COOR_TH = DELTA_T * 50


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers (ported from TrackNetV3_TableTennis/utils/general.py)
# ─────────────────────────────────────────────────────────────────────────────

def _to_img(image: np.ndarray) -> np.ndarray:
    """Convert normalized [0,1] image back to [0,255] uint8."""
    return (image * 255).astype("uint8")


def _to_img_format(inp: np.ndarray, num_ch: int = 1) -> np.ndarray:
    """Transform model output (N, L*C, H, W) to image format (N, L, H, W)."""
    assert len(inp.shape) == 4
    if num_ch == 1:
        return inp
    inp = np.transpose(inp, (0, 2, 3, 1))
    seq_len = int(inp.shape[-1] / num_ch)
    img_seq = np.array([]).reshape(0, seq_len, HEIGHT, WIDTH, 3)
    for n in range(inp.shape[0]):
        frame = np.array([]).reshape(0, HEIGHT, WIDTH, 3)
        for f in range(0, inp.shape[-1], num_ch):
            img = inp[n, :, :, f : f + 3]
            frame = np.concatenate((frame, img.reshape(1, HEIGHT, WIDTH, 3)), axis=0)
        img_seq = np.concatenate((img_seq, frame.reshape(1, seq_len, HEIGHT, WIDTH, 3)), axis=0)
    return img_seq


def _get_model(model_name: str, seq_len: int = None, bg_mode: str = None):
    """Create model by name and configuration."""
    if model_name == "TrackNet":
        if bg_mode == "subtract":
            return TrackNet(in_dim=seq_len, out_dim=seq_len)
        elif bg_mode == "subtract_concat":
            return TrackNet(in_dim=seq_len * 4, out_dim=seq_len)
        elif bg_mode == "concat":
            return TrackNet(in_dim=(seq_len + 1) * 3, out_dim=seq_len)
        else:
            return TrackNet(in_dim=seq_len * 3, out_dim=seq_len)
    elif model_name == "InpaintNet":
        return InpaintNet()
    raise ValueError(f"Invalid model name: {model_name}")


# ─────────────────────────────────────────────────────────────────────────────
# Post-processing helpers (ported from TrackNetV3_TableTennis/test.py)
# ─────────────────────────────────────────────────────────────────────────────

def _predict_location_candidates(
    heatmap: np.ndarray, max_candidates: int = 3, min_area: int = 1
) -> List[Dict[str, Any]]:
    """Extract ball candidate locations from a heatmap via contour detection."""
    if np.amax(heatmap) == 0:
        return []
    cnts, _ = cv2.findContours(heatmap.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for ctr in cnts:
        x, y, w, h = cv2.boundingRect(ctr)
        area = w * h
        if area < min_area:
            continue
        candidates.append({
            "x": x, "y": y, "w": w, "h": h,
            "cx": x + w / 2.0, "cy": y + h / 2.0,
            "area": float(area),
        })
    candidates.sort(key=lambda c: c["area"], reverse=True)
    return candidates[:max_candidates]


def _should_reset_track(
    history: List[Tuple[float, float, int]],
    frame_w: int, frame_h: int,
    border_margin: int = 40,
    stale_frames: int = 6,
    stale_avg_step_thresh: float = 6.5,
    stale_y_span_thresh: float = 12.0,
    stale_x_span_thresh: float = 35.0,
) -> Tuple[bool, Optional[str]]:
    """Determine if the tracking state should be reset (border exit or stale ball)."""
    valid_history = [(x, y) for (x, y, vis) in history if vis == 1]
    if len(valid_history) < 2:
        return False, None

    x1, y1 = valid_history[-2]
    x2, y2 = valid_history[-1]
    vx, vy = x2 - x1, y2 - y1

    near_border = (
        x2 < border_margin or x2 > (frame_w - 1 - border_margin) or
        y2 < border_margin or y2 > (frame_h - 1 - border_margin)
    )
    moving_outward = (
        (x2 < border_margin and vx < 0) or
        (x2 > (frame_w - 1 - border_margin) and vx > 0) or
        (y2 < border_margin and vy < 0) or
        (y2 > (frame_h - 1 - border_margin) and vy > 0)
    )
    if near_border and moving_outward:
        return True, "border_out"

    if len(valid_history) >= stale_frames:
        recent = valid_history[-stale_frames:]
        xs = [p[0] for p in recent]
        ys = [p[1] for p in recent]
        x_span = max(xs) - min(xs)
        y_span = max(ys) - min(ys)
        step_dists = [
            math.hypot(recent[i][0] - recent[i - 1][0], recent[i][1] - recent[i - 1][1])
            for i in range(1, len(recent))
        ]
        avg_step = sum(step_dists) / max(len(step_dists), 1)
        if avg_step <= stale_avg_step_thresh and y_span <= stale_y_span_thresh and x_span <= stale_x_span_thresh:
            return True, "stale_ball"

    return False, None


def _select_best_candidate(
    candidates: List[Dict],
    history: List[Tuple],
    miss_count: int = 0,
    min_area_no_history: float = 6.0,
    min_area_with_history: float = 2.0,
    min_y: float = 400,
    max_y: float = 1050,
) -> Optional[Dict]:
    """Select the most reasonable ball candidate from one heatmap frame."""
    if not candidates:
        return None
    candidates = [c for c in candidates if min_y <= c["cy"] <= max_y]
    if not candidates:
        return None

    valid_history = [(x, y) for (x, y, vis) in history if vis == 1]

    if not valid_history:
        valid_candidates = [c for c in candidates if c["area"] >= min_area_no_history]
        return max(valid_candidates, key=lambda c: c["area"]) if valid_candidates else None

    last_x, last_y = valid_history[-1]
    hist_dx, hist_dy = 0.0, 0.0
    if len(valid_history) >= 2:
        prev_x, prev_y = valid_history[-2]
        hist_dx = last_x - prev_x
        hist_dy = last_y - prev_y

    if miss_count == 0:
        max_x_gap = 130.0
    elif miss_count <= 3:
        max_x_gap = 350.0
    else:
        max_x_gap = 550.0

    valid_candidates = []
    for c in candidates:
        cx, cy = c["cx"], c["cy"]
        area = c["area"]
        if area < min_area_with_history:
            continue
        dx = cx - last_x
        x_to_last = abs(dx)
        y_to_last = abs(cy - last_y)
        pred_x = last_x + hist_dx
        pred_y = last_y + hist_dy
        x_to_pred = abs(cx - pred_x)
        y_to_pred = abs(cy - pred_y)
        if y_to_last > 100 or x_to_last > max_x_gap:
            continue
        if len(valid_history) >= 2 and miss_count == 0:
            if hist_dx > 12 and dx < -12:
                continue
            if hist_dx < -12 and dx > 12:
                continue
            if x_to_pred > 120 or y_to_pred > 80:
                continue
        dist = math.hypot(cx - last_x, cy - last_y)
        valid_candidates.append({"cand": c, "dist": dist})

    if not valid_candidates:
        return None
    return min(valid_candidates, key=lambda v: v["dist"])["cand"]


def _get_ensemble_weight(seq_len: int, eval_mode: str) -> "torch.Tensor":
    """Get weight for temporal ensemble."""
    if eval_mode == "average":
        weight = torch.ones(seq_len) / seq_len
    elif eval_mode == "weight":
        weight = torch.ones(seq_len)
        for i in range(math.ceil(seq_len / 2)):
            weight[i] = i + 1
            weight[seq_len - i - 1] = i + 1
        weight = weight / weight.sum()
    else:
        raise ValueError(f"Invalid eval_mode: {eval_mode}")
    return weight


def _generate_inpaint_mask(
    pred_dict: Dict,
    frame_w: int, frame_h: int,
    max_gap: int = 14,
    border_margin_x: int = 160,
    max_angle_diff: float = 100.0,
    min_valid_run: int = 1,
    angle_check_min_gap: int = 14,
    max_reverse_dx: float = 40.0,
) -> List[int]:
    """Generate inpaint mask for InpaintNet (ported from test.py)."""
    x = np.asarray(pred_dict["X"], dtype=float)
    y = np.asarray(pred_dict["Y"], dtype=float)
    vis = np.asarray(pred_dict["Visibility"], dtype=int)
    n = len(vis)
    mask = np.zeros(n, dtype=int)

    def near_border(px, py):
        return px > (frame_w - 1 - border_margin_x)

    def find_prev_visible(idx):
        k = idx
        while k >= 0 and vis[k] == 0:
            k -= 1
        return k

    def find_next_visible(idx):
        k = idx
        while k < n and vis[k] == 0:
            k += 1
        return k

    def count_visible_backward(idx, limit=10):
        cnt, k = 0, idx
        while k >= 0 and cnt < limit:
            if vis[k] == 1:
                cnt += 1
            else:
                break
            k -= 1
        return cnt

    def count_visible_forward(idx, limit=10):
        cnt, k = 0, idx
        while k < n and cnt < limit:
            if vis[k] == 1:
                cnt += 1
            else:
                break
            k += 1
        return cnt

    def vec_angle_deg(v1, v2):
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 < 1e-6 or n2 < 1e-6:
            return 0.0
        c = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
        return float(np.degrees(np.arccos(c)))

    i = 0
    while i < n:
        if vis[i] == 1:
            i += 1
            continue
        start = i
        while i < n and vis[i] == 0:
            i += 1
        end = i
        gap_len = end - start
        if start == 0 or end == n:
            continue
        if gap_len > max_gap:
            continue

        prev_idx = find_prev_visible(start - 1)
        next_idx = find_next_visible(end)
        if prev_idx < 0 or next_idx >= n:
            continue
        if near_border(x[prev_idx], y[prev_idx]) or near_border(x[next_idx], y[next_idx]):
            continue
        if count_visible_backward(prev_idx) < min_valid_run:
            continue
        if count_visible_forward(next_idx) < min_valid_run:
            continue

        if gap_len < angle_check_min_gap:
            mask[start:end] = 1
            continue

        prev2_idx = find_prev_visible(prev_idx - 1)
        next2_idx = find_next_visible(next_idx + 1)
        if prev2_idx >= 0 and next2_idx < n:
            dx_before = x[prev_idx] - x[prev2_idx]
            dx_after = x[next2_idx] - x[next_idx]
            if dx_before < -max_reverse_dx and dx_after > max_reverse_dx:
                continue
            if dx_before > max_reverse_dx and dx_after < -max_reverse_dx:
                continue
            v_before = np.array([x[prev_idx] - x[prev2_idx], y[prev_idx] - y[prev2_idx]], dtype=float)
            v_after = np.array([x[next2_idx] - x[next_idx], y[next2_idx] - y[next_idx]], dtype=float)
            if vec_angle_deg(v_before, v_after) > max_angle_diff:
                continue

        mask[start:end] = 1

    return mask.tolist()


# ─────────────────────────────────────────────────────────────────────────────
# Video Iterable Dataset (ported from TrackNetV3_TableTennis/dataset.py)
# ─────────────────────────────────────────────────────────────────────────────

if TORCH_AVAILABLE:
    class _VideoIterableDataset(IterableDataset):
        """Memory-efficient streaming dataset for large video inference."""

        def __init__(self, video_file: str, seq_len: int = 8, sliding_step: int = 1,
                     bg_mode: str = "", max_sample_num: int = 1800, video_range=None):
            self.HEIGHT = HEIGHT
            self.WIDTH = WIDTH
            self.video_file = video_file
            cap = cv2.VideoCapture(self.video_file)
            self.video_len = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = int(cap.get(cv2.CAP_PROP_FPS))
            self.w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            self.w_scaler = self.w / self.WIDTH
            self.h_scaler = self.h / self.HEIGHT
            self.seq_len = seq_len
            self.sliding_step = sliding_step
            self.bg_mode = bg_mode

            if self.bg_mode:
                self.median = self._gen_median(max_sample_num, video_range)
            if self.bg_mode in ("subtract", "subtract_concat"):
                self._median_hwc_i16 = self._get_median_hwc().astype(np.int16)
            if self.bg_mode == "concat":
                self._median_chw_f32 = self._get_median_chw().astype(np.float32) / 255.0

        def _gen_median(self, max_sample_num: int, video_range) -> np.ndarray:
            """Generate median background image by sampling frames."""
            cap = cv2.VideoCapture(self.video_file)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30

            if video_range:
                start_f = video_range[0] * fps
                end_f = min(video_range[1] * fps, total)
            else:
                start_f = 0
                end_f = total

            frame_count = end_f - start_f
            step = max(1, frame_count // max_sample_num)
            sampled = []

            for f_idx in range(start_f, end_f, step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
                ret, frame = cap.read()
                if not ret:
                    break
                resized = cv2.resize(frame, (self.WIDTH, self.HEIGHT))
                rgb = resized[..., ::-1]  # BGR -> RGB
                sampled.append(rgb)
                if len(sampled) >= max_sample_num:
                    break

            cap.release()
            if not sampled:
                return np.zeros((self.HEIGHT, self.WIDTH, 3), dtype=np.uint8)
            return np.median(np.array(sampled), axis=0).astype(np.uint8)

        def _get_median_hwc(self) -> np.ndarray:
            return self.median  # (H, W, 3) uint8

        def _get_median_chw(self) -> np.ndarray:
            return self.median.transpose(2, 0, 1)  # (3, H, W)

        def _preprocess_one_frame(self, frame_bgr: np.ndarray) -> np.ndarray:
            """Process a single frame → (C, H, W) float32 in [0,1]."""
            rgb = cv2.resize(frame_bgr, (self.WIDTH, self.HEIGHT), interpolation=cv2.INTER_LINEAR)
            rgb = rgb[..., ::-1]  # BGR → RGB

            if not self.bg_mode:
                return rgb.transpose(2, 0, 1).astype(np.float32) / 255.0
            if self.bg_mode == "subtract":
                diff = np.abs(rgb.astype(np.int16) - self._median_hwc_i16).sum(axis=2)
                return (diff.astype(np.float32) / 255.0)[np.newaxis]
            if self.bg_mode == "subtract_concat":
                diff = np.abs(rgb.astype(np.int16) - self._median_hwc_i16).sum(axis=2)
                rgb_chw = rgb.transpose(2, 0, 1).astype(np.float32) / 255.0
                diff_chw = (diff.astype(np.float32) / 255.0)[np.newaxis]
                return np.concatenate([rgb_chw, diff_chw], axis=0)
            if self.bg_mode == "concat":
                return rgb.transpose(2, 0, 1).astype(np.float32) / 255.0
            raise ValueError(f"Unknown bg_mode: {self.bg_mode}")

        def _assemble(self, buf: deque) -> np.ndarray:
            """Assemble deque of preprocessed frames into a single sample tensor."""
            frames_list = list(buf)
            if self.bg_mode == "concat":
                stacked = np.concatenate([self._median_chw_f32] + frames_list, axis=0)
            else:
                stacked = np.concatenate(frames_list, axis=0)
            return stacked

        def __iter__(self):
            """Stream frames with sliding window."""
            cap = cv2.VideoCapture(self.video_file)
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            buf = deque(maxlen=self.seq_len)
            next_read_f_id = 0

            while len(buf) < self.seq_len:
                success, frame = cap.read()
                if not success:
                    break
                buf.append(self._preprocess_one_frame(frame))
                next_read_f_id += 1

            if len(buf) == 0:
                cap.release()
                return
            while len(buf) < self.seq_len:
                buf.append(buf[-1].copy())

            while True:
                end_f_id = next_read_f_id
                seq_start = end_f_id - self.seq_len
                data_idx = np.array([(0, seq_start + i) for i in range(self.seq_len)])
                frames = self._assemble(buf)
                yield data_idx, frames

                # Slide forward
                advanced = 0
                for _ in range(self.sliding_step):
                    success, frame = cap.read()
                    if not success:
                        cap.release()
                        return
                    buf.append(self._preprocess_one_frame(frame))
                    next_read_f_id += 1
                    advanced += 1

    class _ShuttlecockTrajectoryDataset(torch.utils.data.Dataset):
        """Dataset for InpaintNet coordinate-based inference."""

        def __init__(self, seq_len: int, sliding_step: int, pred_dict: Dict,
                     data_mode: str = "coordinate", padding: bool = False):
            self.seq_len = seq_len
            self.sliding_step = sliding_step
            self.data_mode = data_mode

            frames = pred_dict["Frame"]
            x_arr = np.array(pred_dict["X"], dtype=float)
            y_arr = np.array(pred_dict["Y"], dtype=float)
            vis_arr = np.array(pred_dict["Visibility"], dtype=int)
            w_scaler, h_scaler = pred_dict["Img_scaler"]
            w_total = int(w_scaler * WIDTH)
            h_total = int(h_scaler * HEIGHT)

            # Normalize coordinates to [0, 1]
            self.coor_x = x_arr / w_total if w_total > 0 else x_arr
            self.coor_y = y_arr / h_total if h_total > 0 else y_arr
            self.vis = vis_arr
            self.inpaint_mask = np.array(pred_dict.get("Inpaint_Mask", [0] * len(frames)), dtype=float)
            self.num_frames = len(frames)

            # Compute sample indices
            self.indices = []
            if padding:
                for start in range(0, self.num_frames, self.sliding_step):
                    self.indices.append(start)
            else:
                for start in range(0, self.num_frames - seq_len + 1, self.sliding_step):
                    self.indices.append(start)

        def __len__(self):
            return len(self.indices)

        def __getitem__(self, idx):
            start = self.indices[idx]
            end = min(start + self.seq_len, self.num_frames)

            # Build coordinate tensor (seq_len, 2) and mask tensor (seq_len, 1)
            coor = np.zeros((self.seq_len, 2), dtype=np.float32)
            mask = np.zeros((self.seq_len, 1), dtype=np.float32)
            data_idx = np.zeros((self.seq_len, 2), dtype=np.float32)

            for i, f_idx in enumerate(range(start, start + self.seq_len)):
                if f_idx < self.num_frames:
                    coor[i, 0] = self.coor_x[f_idx]
                    coor[i, 1] = self.coor_y[f_idx]
                    mask[i, 0] = self.inpaint_mask[f_idx]
                    data_idx[i] = [0, f_idx]
                else:
                    # Padding: repeat last
                    coor[i] = coor[i - 1]
                    data_idx[i] = [0, f_idx]

            return data_idx, coor, mask


# ─────────────────────────────────────────────────────────────────────────────
# Core predict() function (ported from predict.py)
# ─────────────────────────────────────────────────────────────────────────────

@contextmanager
def _nullctx():
    yield


def _predict(
    indices,
    y_pred=None,
    c_pred=None,
    img_scaler: Tuple[float, float] = (1, 1),
    track_state: Optional[Dict] = None,
    stale_blank_frames: int = 10,
) -> Tuple[Dict, Dict]:
    """
    Post-process TrackNet/InpaintNet output for a batch of sequences.

    Returns pred_dict and updated track_state.
    """
    if track_state is None:
        track_state = {
            "history": [], "miss_count": 0,
            "ignore_stale_until": -1, "ignore_stale_pos": None,
            "stale_blank_until": -1,
        }

    MAX_CANDIDATES = 3
    HISTORY_SIZE = 8
    pred_dict = {"Frame": [], "X": [], "Y": [], "Visibility": [], "Force_Blank": []}
    batch_size, seq_len = indices.shape[0], indices.shape[1]

    indices_np = indices.detach().cpu().numpy() if torch.is_tensor(indices) else indices
    if y_pred is not None:
        y_pred = (y_pred > 0.5)
        y_pred = y_pred.detach().cpu().numpy() if torch.is_tensor(y_pred) else y_pred
        y_pred = _to_img_format(y_pred)
    if c_pred is not None:
        c_pred = c_pred.detach().cpu().numpy() if torch.is_tensor(c_pred) else c_pred

    prev_f_i = -1
    for n_idx in range(batch_size):
        for f in range(seq_len):
            f_i = indices_np[n_idx][f][1]
            if f_i != prev_f_i:
                force_blank = 0
                cx_pred, cy_pred = 0, 0

                if y_pred is not None and int(f_i) <= int(track_state.get("stale_blank_until", -1)):
                    cx_pred, cy_pred = 0, 0
                    force_blank = 1
                    track_state["history"] = []
                    track_state["miss_count"] = 0

                elif c_pred is not None:
                    c_p = c_pred[n_idx][f]
                    cx_pred = int(c_p[0] * WIDTH * img_scaler[0])
                    cy_pred = int(c_p[1] * HEIGHT * img_scaler[1])

                elif y_pred is not None:
                    y_p = y_pred[n_idx][f]
                    heatmap = _to_img(y_p)
                    candidates = _predict_location_candidates(heatmap, max_candidates=MAX_CANDIDATES)

                    scaled_candidates = []
                    for c in candidates:
                        scaled_candidates.append({
                            "x": int(c["x"] * img_scaler[0]),
                            "y": int(c["y"] * img_scaler[1]),
                            "w": int(c["w"] * img_scaler[0]),
                            "h": int(c["h"] * img_scaler[1]),
                            "cx": c["cx"] * img_scaler[0],
                            "cy": c["cy"] * img_scaler[1],
                            "area": c["area"],
                        })

                    frame_w = int(WIDTH * img_scaler[0])
                    frame_h = int(HEIGHT * img_scaler[1])

                    need_reset, reset_reason = _should_reset_track(
                        track_state["history"],
                        frame_w=frame_w, frame_h=frame_h,
                    )

                    if need_reset and reset_reason == "stale_ball":
                        valid_history = [(x, y) for (x, y, vis) in track_state["history"] if vis == 1]
                        last_valid = valid_history[-1] if valid_history else None
                        if last_valid is not None:
                            blank_n = int(max(0, stale_blank_frames))
                            if blank_n > 0:
                                track_state["stale_blank_until"] = int(f_i) + blank_n - 1
                                track_state["ignore_stale_until"] = int(f_i) + 80
                                track_state["ignore_stale_pos"] = last_valid
                                track_state["history"] = []
                                track_state["miss_count"] = 0
                                cx_pred, cy_pred = 0, 0
                                force_blank = 1

                    if force_blank:
                        chosen = None
                    else:
                        select_history = [] if need_reset else track_state["history"]
                        select_miss_count = 0 if need_reset else track_state["miss_count"]

                        # Filter stale position candidates
                        if (track_state.get("ignore_stale_pos") is not None and
                                int(f_i) <= track_state.get("ignore_stale_until", -1)):
                            sx, sy = track_state["ignore_stale_pos"]
                            scaled_candidates = [
                                c for c in scaled_candidates
                                if not (abs(c["cx"] - sx) <= 80 and abs(c["cy"] - sy) <= 50)
                            ]

                        chosen = _select_best_candidate(
                            candidates=scaled_candidates,
                            history=select_history,
                            miss_count=select_miss_count,
                        )

                    if force_blank:
                        pass
                    elif chosen is None:
                        cx_pred, cy_pred = 0, 0
                        if need_reset:
                            track_state["history"] = []
                            track_state["miss_count"] = 0
                        else:
                            track_state["miss_count"] += 1
                            track_state["history"].append((0, 0, 0))
                    else:
                        cx_pred = int(chosen["cx"])
                        cy_pred = int(chosen["cy"])
                        track_state["ignore_stale_until"] = -1
                        track_state["ignore_stale_pos"] = None
                        if need_reset:
                            track_state["history"] = [(cx_pred, cy_pred, 1)]
                            track_state["miss_count"] = 0
                        else:
                            track_state["history"].append((cx_pred, cy_pred, 1))
                            track_state["miss_count"] = 0

                    if len(track_state["history"]) > HISTORY_SIZE:
                        track_state["history"] = track_state["history"][-HISTORY_SIZE:]
                else:
                    raise ValueError("Invalid input: neither y_pred nor c_pred provided")

                vis_pred = 0 if cx_pred == 0 and cy_pred == 0 else 1
                pred_dict["Frame"].append(int(f_i))
                pred_dict["X"].append(cx_pred)
                pred_dict["Y"].append(cy_pred)
                pred_dict["Visibility"].append(vis_pred)
                pred_dict["Force_Blank"].append(int(force_blank))
                prev_f_i = f_i
            else:
                break

    return pred_dict, track_state


def _write_pred_csv(pred_dict: Dict, save_file: str):
    """Write prediction result to CSV file."""
    n = len(pred_dict["Frame"])
    inpaint_mask = pred_dict.get("Inpaint_Mask", [0] * n)

    with open(save_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Frame", "Visibility", "X", "Y", "Inpaint_Mask"])
        for i in range(n):
            writer.writerow([
                pred_dict["Frame"][i],
                pred_dict["Visibility"][i],
                pred_dict["X"][i],
                pred_dict["Y"][i],
                inpaint_mask[i] if i < len(inpaint_mask) else 0,
            ])


# ─────────────────────────────────────────────────────────────────────────────
# Public API: run_tracknet_inference()
# ─────────────────────────────────────────────────────────────────────────────

def run_tracknet_inference(
    video_path: str,
    output_csv: str,
    tracknet_weights: str,
    inpaintnet_weights: Optional[str] = None,
    batch_size: int = 16,
    eval_mode: str = "weight",
    stale_blank_frames: int = 10,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> str:
    """
    Run full TrackNet + InpaintNet inference on a video file and output a ball CSV.

    Args:
        video_path: Path to the input 720p video.
        output_csv: Path to write the output ball CSV.
        tracknet_weights: Path to TrackNet_best.pt checkpoint.
        inpaintnet_weights: Path to InpaintNet_best.pt checkpoint (optional).
        batch_size: Inference batch size (default: 16).
        eval_mode: Temporal ensemble mode ('weight', 'average', 'nonoverlap').
        stale_blank_frames: Frames to blank after stale ball detection.
        progress_callback: Callback receiving (percent, stage_description).

    Returns:
        Path to the output CSV file.
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is required for TrackNet inference. Install with: pip install torch torchvision")
    if not CV2_AVAILABLE:
        raise ImportError("OpenCV is required for TrackNet inference. Install with: pip install opencv-python")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"TrackNet inference device: {device}")

    if progress_callback:
        progress_callback(0, f"Loading TrackNet model on {device}...")

    # ── Load Models ──────────────────────────────────────────────────────────
    tracknet_ckpt = torch.load(tracknet_weights, map_location="cpu", weights_only=False)
    tracknet_seq_len = tracknet_ckpt["param_dict"]["seq_len"]
    bg_mode = tracknet_ckpt["param_dict"]["bg_mode"]
    tracknet = _get_model("TrackNet", tracknet_seq_len, bg_mode).to(device)
    tracknet.load_state_dict(tracknet_ckpt["model"])
    tracknet.eval()

    inpaintnet = None
    inpaintnet_seq_len = None
    if inpaintnet_weights and os.path.exists(inpaintnet_weights):
        inpaintnet_ckpt = torch.load(inpaintnet_weights, map_location="cpu", weights_only=False)
        inpaintnet_seq_len = inpaintnet_ckpt["param_dict"]["seq_len"]
        inpaintnet = _get_model("InpaintNet").to(device)
        inpaintnet.load_state_dict(inpaintnet_ckpt["model"])
        inpaintnet.eval()
        logger.info("InpaintNet loaded successfully")

    # ── Video metadata ───────────────────────────────────────────────────────
    cap = cv2.VideoCapture(video_path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video_len = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 60.0
    cap.release()

    w_scaler = w / WIDTH
    h_scaler = h / HEIGHT
    img_scaler = (w_scaler, h_scaler)
    logger.info(f"Video: {video_path} ({w}x{h}, {video_len} frames @ {fps:.1f} fps)")

    if progress_callback:
        progress_callback(5, f"Preparing dataset ({video_len} frames)...")

    # ── Build Dataset ────────────────────────────────────────────────────────
    sliding_step = tracknet_seq_len if eval_mode == "nonoverlap" else 1
    dataset = _VideoIterableDataset(
        video_path, seq_len=tracknet_seq_len, sliding_step=sliding_step,
        bg_mode=bg_mode, max_sample_num=150,
    )
    data_loader = DataLoader(
        dataset, batch_size=batch_size, shuffle=False, drop_last=False,
        num_workers=1, prefetch_factor=4,
    )

    # ── TrackNet Inference ───────────────────────────────────────────────────
    tracknet_pred_dict = {
        "Frame": [], "X": [], "Y": [], "Visibility": [], "Force_Blank": [], "Inpaint_Mask": [],
        "Img_scaler": (w_scaler, h_scaler), "Img_shape": (w, h),
    }
    track_state = {
        "history": [], "miss_count": 0,
        "ignore_stale_until": -1, "ignore_stale_pos": None,
        "stale_blank_until": -1,
    }

    if progress_callback:
        progress_callback(10, "Running TrackNet ball detection inference...")

    if eval_mode == "nonoverlap":
        for step, (i, x) in enumerate(data_loader):
            x = x.float().to(device)
            with torch.no_grad():
                y_pred = tracknet(x).detach().cpu()
            tmp_pred, track_state = _predict(
                i, y_pred=y_pred, img_scaler=img_scaler,
                track_state=track_state, stale_blank_frames=stale_blank_frames,
            )
            for key in tmp_pred:
                tracknet_pred_dict[key].extend(tmp_pred[key])

            if progress_callback and step % 10 == 0:
                frames_done = len(tracknet_pred_dict["Frame"])
                pct = min(50, 10 + int((frames_done / max(video_len, 1)) * 40))
                progress_callback(pct, f"TrackNet: {frames_done}/{video_len} frames")
    else:
        # Weighted temporal ensemble
        seq_len = tracknet_seq_len
        num_sample = video_len - seq_len + 1
        sample_count = 0
        buffer_size = seq_len - 1
        batch_i = torch.arange(seq_len)
        frame_i = torch.arange(seq_len - 1, -1, -1)
        y_pred_buffer = torch.zeros((buffer_size, seq_len, HEIGHT, WIDTH), dtype=torch.float32)
        weight = _get_ensemble_weight(seq_len, eval_mode)

        for step, (i, x) in enumerate(data_loader):
            x = x.float().to(device)
            b_size = i.shape[0]

            with torch.no_grad():
                y_pred = tracknet(x).detach().cpu()

            y_pred_buffer = torch.cat((y_pred_buffer, y_pred), dim=0)
            ensemble_i = torch.empty((0, 1, 2), dtype=torch.float32)
            ensemble_y_pred = torch.empty((0, 1, HEIGHT, WIDTH), dtype=torch.float32)

            for b in range(b_size):
                if sample_count < buffer_size:
                    y_pred_e = y_pred_buffer[batch_i + b, frame_i].sum(0) / (sample_count + 1)
                else:
                    y_pred_e = (y_pred_buffer[batch_i + b, frame_i] * weight[:, None, None]).sum(0)

                ensemble_i = torch.cat((ensemble_i, i[b][0].reshape(1, 1, 2)), dim=0)
                ensemble_y_pred = torch.cat((ensemble_y_pred, y_pred_e.reshape(1, 1, HEIGHT, WIDTH)), dim=0)
                sample_count += 1

                if sample_count == num_sample:
                    y_zero_pad = torch.zeros((buffer_size, seq_len, HEIGHT, WIDTH), dtype=torch.float32)
                    y_pred_buffer = torch.cat((y_pred_buffer, y_zero_pad), dim=0)
                    for f_offset in range(1, seq_len):
                        y_pred_e = y_pred_buffer[batch_i + b + f_offset, frame_i].sum(0) / (seq_len - f_offset)
                        ensemble_i = torch.cat((ensemble_i, i[-1][f_offset].reshape(1, 1, 2)), dim=0)
                        ensemble_y_pred = torch.cat((ensemble_y_pred, y_pred_e.reshape(1, 1, HEIGHT, WIDTH)), dim=0)

            tmp_pred, track_state = _predict(
                ensemble_i, y_pred=ensemble_y_pred, img_scaler=img_scaler,
                track_state=track_state, stale_blank_frames=stale_blank_frames,
            )
            for key in tmp_pred:
                tracknet_pred_dict[key].extend(tmp_pred[key])

            y_pred_buffer = y_pred_buffer[-buffer_size:]

            if progress_callback and step % 10 == 0:
                frames_done = len(tracknet_pred_dict["Frame"])
                pct = min(50, 10 + int((frames_done / max(video_len, 1)) * 40))
                progress_callback(pct, f"TrackNet: {frames_done}/{video_len} frames")

    logger.info(f"TrackNet inference complete: {len(tracknet_pred_dict['Frame'])} frame predictions")

    # ── InpaintNet Inference ─────────────────────────────────────────────────
    if inpaintnet is not None:
        if progress_callback:
            progress_callback(55, "Running InpaintNet trajectory inpainting...")

        tracknet_pred_dict["Inpaint_Mask"] = _generate_inpaint_mask(
            tracknet_pred_dict, frame_w=w, frame_h=h,
        )

        # Prevent InpaintNet from refilling force-blanked frames
        if "Force_Blank" in tracknet_pred_dict:
            force_blank_arr = np.asarray(tracknet_pred_dict["Force_Blank"], dtype=int)
            inpaint_mask_arr = np.asarray(tracknet_pred_dict["Inpaint_Mask"], dtype=int)
            if len(force_blank_arr) == len(inpaint_mask_arr):
                inpaint_mask_arr[force_blank_arr == 1] = 0
                tracknet_pred_dict["Inpaint_Mask"] = inpaint_mask_arr.tolist()

        inpaint_pred_dict = {"Frame": [], "X": [], "Y": [], "Visibility": [], "Force_Blank": []}
        inp_sliding_step = inpaintnet_seq_len if eval_mode == "nonoverlap" else 1

        inp_dataset = _ShuttlecockTrajectoryDataset(
            seq_len=inpaintnet_seq_len, sliding_step=inp_sliding_step,
            pred_dict=tracknet_pred_dict, data_mode="coordinate",
            padding=(eval_mode == "nonoverlap"),
        )
        inp_loader = DataLoader(
            inp_dataset, batch_size=batch_size, shuffle=False,
            num_workers=0, drop_last=False,
        )

        if eval_mode == "nonoverlap":
            for step, (i, coor_pred, inpaint_mask) in enumerate(inp_loader):
                coor_pred, inpaint_mask = coor_pred.float(), inpaint_mask.float()
                with torch.no_grad():
                    coor_inpaint = inpaintnet(coor_pred.to(device), inpaint_mask.to(device)).detach().cpu()
                    coor_inpaint = coor_inpaint * inpaint_mask + coor_pred * (1 - inpaint_mask)

                th_mask = (coor_inpaint[:, :, 0] < COOR_TH) & (coor_inpaint[:, :, 1] < COOR_TH)
                coor_inpaint[th_mask] = 0.0
                tmp_pred, _ = _predict(i, c_pred=coor_inpaint, img_scaler=img_scaler)
                for key in tmp_pred:
                    inpaint_pred_dict[key].extend(tmp_pred[key])

                if progress_callback and step % 10 == 0:
                    progress_callback(65, f"InpaintNet: step {step}")
        else:
            # Weighted ensemble for InpaintNet
            inp_weight = _get_ensemble_weight(inpaintnet_seq_len, eval_mode)
            inp_num_sample = len(inp_dataset)
            inp_sample_count = 0
            inp_buffer_size = inpaintnet_seq_len - 1
            inp_batch_i = torch.arange(inpaintnet_seq_len)
            inp_frame_i = torch.arange(inpaintnet_seq_len - 1, -1, -1)
            coor_inpaint_buffer = torch.zeros((inp_buffer_size, inpaintnet_seq_len, 2), dtype=torch.float32)

            for step, (i, coor_pred, inpaint_mask) in enumerate(inp_loader):
                coor_pred, inpaint_mask = coor_pred.float(), inpaint_mask.float()
                b_size = i.shape[0]

                with torch.no_grad():
                    coor_inpaint = inpaintnet(coor_pred.to(device), inpaint_mask.to(device)).detach().cpu()
                    coor_inpaint = coor_inpaint * inpaint_mask + coor_pred * (1 - inpaint_mask)

                th_mask = (coor_inpaint[:, :, 0] < COOR_TH) & (coor_inpaint[:, :, 1] < COOR_TH)
                coor_inpaint[th_mask] = 0.0
                coor_inpaint_buffer = torch.cat((coor_inpaint_buffer, coor_inpaint), dim=0)
                ensemble_i = torch.empty((0, 1, 2), dtype=torch.float32)
                ensemble_coor = torch.empty((0, 1, 2), dtype=torch.float32)

                for b in range(b_size):
                    if inp_sample_count < inp_buffer_size:
                        ci = coor_inpaint_buffer[inp_batch_i + b, inp_frame_i].sum(0) / (inp_sample_count + 1)
                    else:
                        ci = (coor_inpaint_buffer[inp_batch_i + b, inp_frame_i] * inp_weight[:, None]).sum(0)
                    ensemble_i = torch.cat((ensemble_i, i[b][0].view(1, 1, 2)), dim=0)
                    ensemble_coor = torch.cat((ensemble_coor, ci.view(1, 1, 2)), dim=0)
                    inp_sample_count += 1

                    if inp_sample_count == inp_num_sample:
                        coor_zero_pad = torch.zeros((inp_buffer_size, inpaintnet_seq_len, 2), dtype=torch.float32)
                        coor_inpaint_buffer = torch.cat((coor_inpaint_buffer, coor_zero_pad), dim=0)
                        for f_offset in range(1, inpaintnet_seq_len):
                            ci = coor_inpaint_buffer[inp_batch_i + b + f_offset, inp_frame_i].sum(0) / (inpaintnet_seq_len - f_offset)
                            ensemble_i = torch.cat((ensemble_i, i[-1][f_offset].view(1, 1, 2)), dim=0)
                            ensemble_coor = torch.cat((ensemble_coor, ci.view(1, 1, 2)), dim=0)

                th_mask_ens = (ensemble_coor[:, :, 0] < COOR_TH) & (ensemble_coor[:, :, 1] < COOR_TH)
                ensemble_coor[th_mask_ens] = 0.0
                tmp_pred, _ = _predict(ensemble_i, c_pred=ensemble_coor, img_scaler=img_scaler)
                for key in tmp_pred:
                    inpaint_pred_dict[key].extend(tmp_pred[key])

                coor_inpaint_buffer = coor_inpaint_buffer[-inp_buffer_size:]

                if progress_callback and step % 10 == 0:
                    progress_callback(65, f"InpaintNet ensemble: step {step}")

        # Use inpainted predictions as final
        pred_dict = inpaint_pred_dict
        if "Force_Blank" in tracknet_pred_dict:
            if len(tracknet_pred_dict["Force_Blank"]) == len(pred_dict.get("Frame", [])):
                pred_dict["Force_Blank"] = list(tracknet_pred_dict["Force_Blank"])
        if "Inpaint_Mask" not in pred_dict:
            pred_dict["Inpaint_Mask"] = tracknet_pred_dict.get("Inpaint_Mask", [0] * len(pred_dict["Frame"]))
    else:
        pred_dict = tracknet_pred_dict

    # ── Write output CSV ─────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)
    if progress_callback:
        progress_callback(90, "Writing ball trajectory CSV...")

    _write_pred_csv(pred_dict, output_csv)
    logger.info(f"Ball CSV saved: {output_csv} ({len(pred_dict['Frame'])} frames)")

    if progress_callback:
        progress_callback(100, f"TrackNet complete: {len(pred_dict['Frame'])} frames → {output_csv}")

    return output_csv
