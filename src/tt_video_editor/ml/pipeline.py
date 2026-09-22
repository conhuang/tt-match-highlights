"""
Master AI Rally Detection Pipeline.

Coordinates the 4-stage pipeline:
1. Fast hardware-accelerated 720p downscaling (transcode.py)
2. TrackNetV3 ball trajectory extraction (TrackNet_best.pt -> ball.csv)
3. High-motion candidate extraction (candidate_extractor.py)
4. Chunked multimodal rally verification via Google Gemini (detector.py)
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Callable

from .transcode import transcode_to_720p
from .tracknet.candidate_extractor import extract_tracknet_candidates
from .gemini.detector import detect_rallies_with_gemini

logger = logging.getLogger("ml.pipeline")


def run_ai_rally_pipeline(
    video_path: str,
    output_dir: str,
    ball_csv_path: Optional[str] = None,
    tracknet_file: Optional[str] = None,
    inpaintnet_file: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    gemini_model: str = "gemini-2.5-flash",
    file_handle: Optional[str] = None,
    chunk_size: float = 300.0,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, Any]:
    """
    Execute the full end-to-end rally detection pipeline.

    Args:
        video_path: Path to the input video file (local or downloaded).
        output_dir: Directory where intermediate artifacts (720p proxy, CSV, JSON) are saved.
        ball_csv_path: Optional path to pre-computed TrackNet ball CSV (skips Step 2).
        tracknet_file: Path to TrackNet_best.pt weights.
        inpaintnet_file: Path to InpaintNet_best.pt weights.
        gemini_api_key: Google Gemini API Key (or env var).
        gemini_model: Gemini model identifier (default: gemini-2.5-flash).
        file_handle: Existing Google AI Studio Files API handle (if pre-uploaded).
        chunk_size: Duration in seconds of each temporal chunk (default: 300s).
        progress_callback: Callback function receiving (percent: int, stage: str).

    Returns:
        Dict containing:
        - "rallies": List of formatted rally events
        - "proxy_720p_path": Path to generated 720p proxy
        - "ball_csv_path": Path to ball CSV
        - "output_json_path": Path to saved output JSON
    """
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(video_path))[0]

    # -------------------------------------------------------------------------
    # Step 1: 720p Hardware-Accelerated Transcode
    # -------------------------------------------------------------------------
    proxy_720p = os.path.join(output_dir, f"{base_name}_720p.mp4")
    if os.path.exists(proxy_720p) and os.path.getsize(proxy_720p) > 0:
        logger.info(f"Using existing 720p proxy: {proxy_720p}")
    else:
        if progress_callback:
            progress_callback(5, "Downscaling video to 720p (Hardware Accelerated)...")
        transcode_to_720p(video_path, proxy_720p, target_height=720)

    # -------------------------------------------------------------------------
    # Step 2: TrackNet Ball Trajectory Extraction
    # -------------------------------------------------------------------------
    active_ball_csv = ball_csv_path
    if not active_ball_csv or not os.path.exists(active_ball_csv):
        target_csv = os.path.join(output_dir, f"{base_name}_ball.csv")
        if os.path.exists(target_csv) and os.path.getsize(target_csv) > 0:
            active_ball_csv = target_csv
            logger.info(f"Using existing ball CSV: {active_ball_csv}")
        elif tracknet_file and os.path.exists(tracknet_file):
            if progress_callback:
                progress_callback(20, "Running TrackNetV3 ball trajectory inference...")
            logger.info(f"Running TrackNet inference on {proxy_720p}...")
            try:
                from .tracknet.tracker import run_tracknet_inference
                active_ball_csv = run_tracknet_inference(
                    video_path=proxy_720p,
                    output_csv=target_csv,
                    tracknet_weights=tracknet_file,
                    inpaintnet_weights=inpaintnet_file,
                    progress_callback=lambda p, s: progress_callback(20 + int(p * 0.35), s) if progress_callback else None
                )
            except Exception as e:
                logger.warning(f"TrackNet inference skipped or failed: {e}. Proceeding with Gemini video-only mode.")
                active_ball_csv = None
        else:
            logger.info("No TrackNet weights or ball CSV provided; proceeding with Gemini multimodal analysis directly.")
            active_ball_csv = None

    # -------------------------------------------------------------------------
    # Step 3: Extract Motion Candidates from Ball CSV
    # -------------------------------------------------------------------------
    candidates = []
    if active_ball_csv and os.path.exists(active_ball_csv):
        if progress_callback:
            progress_callback(55, "Extracting TrackNet ball motion candidates...")
        candidates = extract_tracknet_candidates(active_ball_csv, fps=60.0)
        logger.info(f"Extracted {len(candidates)} TrackNet candidate motion intervals")

    # -------------------------------------------------------------------------
    # Step 4: Chunked Gemini Multimodal Reasoning
    # -------------------------------------------------------------------------
    if progress_callback:
        progress_callback(60, "Uploading to Gemini and initiating chunked analysis...")

    raw_rallies = detect_rallies_with_gemini(
        video_path=proxy_720p,
        file_handle=file_handle,
        all_candidates=candidates,
        chunk_size=chunk_size,
        model_name=gemini_model,
        api_key=gemini_api_key,
        progress_callback=lambda p, s: progress_callback(60 + int((p / 100) * 35), s) if progress_callback else None
    )

    # -------------------------------------------------------------------------
    # Step 5: Format Output for MatchEvent Schema
    # -------------------------------------------------------------------------
    formatted_events = []
    for r in raw_rallies:
        formatted_events.append({
            "start": round(float(r["start_time"]), 2),
            "end": round(float(r["end_time"]), 2),
            "winner": None,
            "timeout_player": None,
            "isHighlight": bool(r.get("is_highlight", False)),
            "summary": r.get("point_summary", ""),
            "shot_count": int(r.get("rally_shot_count", 0)),
            "end_reason": r.get("end_reason", ""),
        })

    # Save output JSON
    output_json_path = os.path.join(output_dir, f"{base_name}_rallies.json")
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(formatted_events, f, indent=2)

    if progress_callback:
        progress_callback(100, f"Complete! Detected {len(formatted_events)} rally intervals.")

    return {
        "rallies": formatted_events,
        "proxy_720p_path": proxy_720p,
        "ball_csv_path": active_ball_csv,
        "output_json_path": output_json_path,
        "candidate_count": len(candidates),
        "rally_count": len(formatted_events),
    }
