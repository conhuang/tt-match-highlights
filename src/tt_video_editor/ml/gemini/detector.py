"""
Chunked Table Tennis Rally Detector using Google Gemini API + TrackNet CV Guidance.

Features:
- Splits long match videos into temporal chunks (default: 300s / 5 mins) to prevent LLM attention decay.
- Injects chunk-specific TrackNet high-speed ball motion candidate intervals into each query.
- Uses Gemini client.chats.create() for consistent structured JSON generation.
- Enforces strict anti-hallucination rules (zero rallies during warmups, timeouts, set breaks).
- Merges, sorts, and de-duplicates intervals across chunk boundaries.
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger("ml.gemini_detector")

DEFAULT_MODEL_FALLBACKS = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-3.5-flash",
]


def clean_json_response(raw_text: str) -> List[Dict[str, Any]]:
    """
    Clean markdown fences (```json ... ```) and parse JSON from LLM response.
    """
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    return json.loads(text)


def merge_adjacent_rallies(rallies: List[Dict[str, Any]], max_gap: float = 1.0) -> List[Dict[str, Any]]:
    """
    Sort and merge any overlapping or near-adjacent intervals across temporal chunk boundaries.

    Args:
        rallies: List of raw candidate rally dicts with 'start_time' and 'end_time'.
        max_gap: Maximum gap in seconds between intervals to consider them part of the same rally.

    Returns:
        Sorted, merged list of rally dicts.
    """
    if not rallies:
        return []

    # Sort by start time
    sorted_r = sorted(rallies, key=lambda x: float(x["start_time"]))
    merged = []
    curr = sorted_r[0].copy()
    curr["start_time"] = round(float(curr["start_time"]), 2)
    curr["end_time"] = round(float(curr["end_time"]), 2)

    for r in sorted_r[1:]:
        s_val = round(float(r["start_time"]), 2)
        e_val = round(float(r["end_time"]), 2)

        if s_val <= curr["end_time"] + max_gap:
            # Overlapping or contiguous interval
            curr["end_time"] = max(curr["end_time"], e_val)
            if r.get("is_highlight"):
                curr["is_highlight"] = True
            # Prefer non-empty summary
            if not curr.get("point_summary") and r.get("point_summary"):
                curr["point_summary"] = r["point_summary"]
        else:
            merged.append(curr)
            curr = r.copy()
            curr["start_time"] = s_val
            curr["end_time"] = e_val

    merged.append(curr)
    return merged


def build_chunk_prompt(
    c_start: float,
    c_end: float,
    chunk_candidates: List[Dict[str, float]]
) -> str:
    """Build the strict anti-hallucination multimodal prompt for a temporal chunk."""
    cand_text = (
        f"\nTrackNet Computer Vision candidate intervals in this window:\n{json.dumps(chunk_candidates, indent=2)}\n"
        if chunk_candidates else ""
    )

    return f"""
You are an expert Olympic table tennis match video analyst.
Analyze ONLY the specific temporal segment from {c_start:.1f} seconds to {c_end:.1f} seconds in this match video.
Identify ONLY genuine, active scoring rally points occurring within [{c_start:.1f}s, {c_end:.1f}s].
{cand_text}
Strict Rules & Constraints (Zero Tolerance for False Positives):
1. VISUAL BALL FLIGHT REQUIREMENT (No Ball = No Rally):
   - A rally ONLY exists if you visually see a ball actively served and struck back-and-forth across the net.
   - NEVER hallucinate or invent a rally when no ball is in play.
2. STRICT REJECTION CRITERIA (DO NOT OUTPUT THESE):
   - ❌ Player bouncing the ball on the paddle or table before starting their serve.
   - ❌ Player casually hitting, rolling, or tossing the ball back to the server.
   - ❌ Players standing, talking, walking, or toweling off during the ~1-minute set breaks between games.
   - ❌ Let serves (serve hits net and lands on receiver side -> replay).
   - ❌ Warmups and practice hits before or after the match.
3. MATCH SCORING STATE MACHINE:
   - Every genuine rally MUST result in an official point scored by one of the players (games played to 11, win by 2).
   - If an action does not contribute to the match score, it is STRICTLY DISALLOWED.
4. TrackNet Guidance:
   - Cross-reference with the TrackNet Computer Vision candidate timestamps above. Genuine rallies coincide with high-speed ball motion across the table.
5. Padding & Boundaries:
   - "start_time": Set to AT LEAST 1.5 seconds BEFORE the server tosses/strikes the ball (to capture serve preparation and stance).
   - "end_time": Set to AT LEAST 1.5 seconds AFTER the point ends / ball hits floor or net (to capture the reaction and point conclusion).
   - Timestamps must be absolute seconds within [{c_start:.1f}, {c_end:.1f}].
6. Minimum Duration & Non-Overlapping:
   - Every rally clip MUST be greater than 2.5 seconds long (duration = end_time - start_time >= 2.5s).
   - Rallies MUST NOT overlap.
7. Output a JSON list of objects, each containing:
   - "start_time": float timestamp in seconds
   - "end_time": float timestamp in seconds
   - "serve_motion_detected": description of server's stance and toss
   - "rally_shot_count": integer number of paddle contacts (must be >= 2 for serve + return)
   - "end_reason": description of how the point concluded (e.g. net error, out of bounds, winner)
   - "point_summary": brief factual description of the rally
   - "is_highlight": boolean (true for high quality rallies >5 shots, smashes, diving saves)
"""


def detect_rallies_with_gemini(
    video_path: Optional[str] = None,
    file_handle: Optional[str] = None,
    all_candidates: Optional[List[Dict[str, float]]] = None,
    total_duration: Optional[float] = None,
    chunk_size: float = 300.0,
    model_name: str = "gemini-2.5-flash",
    api_key: Optional[str] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> List[Dict[str, Any]]:
    """
    Run chunked rally detection using Gemini API with TrackNet CV candidate guidance.

    Args:
        video_path: Path to local video file to upload.
        file_handle: Existing Google AI Studio Files API handle (e.g. 'files/xxx').
        all_candidates: List of candidate intervals from TrackNet candidate extractor.
        total_duration: Total video duration in seconds (auto-detected if omitted).
        chunk_size: Temporal chunk duration in seconds (default: 300s = 5 mins).
        model_name: Primary Gemini model to query.
        api_key: Gemini API Key (falls back to GEMINI_API_KEY environment variable).
        progress_callback: Optional callback receiving (progress_percent, stage_description).

    Returns:
        List of detected, filtered, and merged rally event dicts.
    """
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set. Please provide api_key or set the environment variable.")

    if not video_path and not file_handle:
        raise ValueError("Must provide either video_path or file_handle.")

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise ImportError("google-genai SDK not installed. Run `pip install google-genai`.")

    client = genai.Client(api_key=api_key)
    all_candidates = all_candidates or []

    # 1. Determine Total Match Duration
    if total_duration is None:
        if all_candidates:
            total_duration = max(c["end"] for c in all_candidates) + 10.0
        elif video_path and os.path.exists(video_path):
            try:
                import cv2
                cap = cv2.VideoCapture(video_path)
                fps = cap.get(cv2.CAP_PROP_FPS) or 60.0
                frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                total_duration = frames / fps
                cap.release()
            except Exception:
                total_duration = 1800.0
        else:
            total_duration = 1800.0

    # 2. Upload video or connect to handle
    if file_handle:
        logger.info(f"Connecting to existing Google Files API handle: {file_handle}...")
        video_file = client.files.get(name=file_handle)
    else:
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        logger.info(f"Uploading video {video_path} ({file_size_mb:.1f} MB) to Google AI Studio Files API...")
        if progress_callback:
            progress_callback(5, f"Uploading 720p proxy to Gemini ({file_size_mb:.0f} MB)...")

        video_file = client.files.upload(file=video_path)
        logger.info(f"Uploaded as {video_file.name}. Waiting for processing...")
        while getattr(video_file, "state", None) and video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = client.files.get(name=video_file.name)

    num_chunks = max(1, int((total_duration + chunk_size - 0.01) // chunk_size))
    logger.info(f"Starting chunked analysis: {num_chunks} chunks ({chunk_size}s each) across {total_duration:.1f}s match")

    models_to_try = [model_name] + [m for m in DEFAULT_MODEL_FALLBACKS if m != model_name]
    all_detected_rallies = []

    # 3. Sequential Chunk Analysis
    for chunk_idx in range(num_chunks):
        c_start = chunk_idx * chunk_size
        c_end = min(total_duration, c_start + chunk_size)

        # Progress tracking across chunks (10% to 90%)
        chunk_prog = 10 + int(((chunk_idx) / num_chunks) * 80)
        stage_desc = f"Gemini Analysis Chunk {chunk_idx + 1}/{num_chunks} [{c_start:.0f}s - {c_end:.0f}s]"
        if progress_callback:
            progress_callback(chunk_prog, stage_desc)

        chunk_cands = [c for c in all_candidates if (c_start - 2.0) <= c["start"] <= (c_end + 2.0)]
        prompt = build_chunk_prompt(c_start, c_end, chunk_cands)

        chunk_rallies = []
        for m_name in models_to_try:
            try:
                chat = client.chats.create(model=m_name)
                response = chat.send_message(
                    message=[video_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )
                if response and response.text:
                    chunk_rallies = clean_json_response(response.text)
                    logger.info(f"Chunk {chunk_idx + 1} ({m_name}) detected {len(chunk_rallies)} raw intervals")
                    break
            except Exception as e:
                logger.warning(f"Model {m_name} query failed: {e}. Trying fallback...")
                time.sleep(1)

        # Filter candidates for quality
        for r in chunk_rallies:
            if "start_time" in r and "end_time" in r:
                s_val = float(r["start_time"])
                e_val = float(r["end_time"])
                shot_cnt = int(r.get("rally_shot_count", 2))
                if (e_val - s_val) >= 2.5 and shot_cnt >= 2:
                    all_detected_rallies.append(r)

    # 4. Merge and de-duplicate across chunks
    merged_final = merge_adjacent_rallies(all_detected_rallies, max_gap=1.0)
    if progress_callback:
        progress_callback(95, f"Merged {len(merged_final)} total rally intervals")

    logger.info(f"Completed detection: {len(merged_final)} rallies across {total_duration:.1f}s video")
    return merged_final
