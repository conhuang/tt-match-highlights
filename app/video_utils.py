import os
import subprocess
import json
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

def extract_video_metadata(video_path: str) -> Dict[str, Any]:
    """
    Uses ffprobe to extract video properties (fps, duration, width, height).
    Returns a dictionary containing the extracted attributes.
    """
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return {"fps": None, "duration": None, "width": None, "height": None}

    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate,duration,width,height,nb_frames",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        if "streams" not in data or not data["streams"]:
            return {"fps": None, "duration": None, "width": None, "height": None}

        stream = data["streams"][0]
        
        # Calculate FPS
        fps = None
        if "r_frame_rate" in stream:
            num, den = map(float, stream["r_frame_rate"].split("/"))
            fps = round(num / den, 2) if den != 0 else 30.0

        # Calculate Duration
        duration = float(stream.get("duration", 0))
        if duration == 0 and "nb_frames" in stream and fps:
            duration = round(int(stream["nb_frames"]) / fps, 2)

        width = stream.get("width")
        height = stream.get("height")

        return {
            "fps": fps,
            "duration": duration,
            "width": width,
            "height": height
        }
    except Exception as e:
        logger.warning(f"ffprobe metadata extraction failed for {video_path}: {e}")
        return {"fps": None, "duration": None, "width": None, "height": None}


def generate_frame_thumbnail(video_path: str, output_path: str, timestamp: float = 0.0) -> bool:
    """
    Extracts a JPEG frame snapshot at the specified timestamp using FFmpeg.
    """
    if not os.path.exists(video_path):
        return False
        
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(timestamp),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception as e:
        logger.error(f"Thumbnail generation error at {timestamp}s: {e}")
        return False
