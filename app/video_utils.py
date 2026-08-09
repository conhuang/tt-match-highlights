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
            fps = num / den if den != 0 else 30.0

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


def optimize_video_for_faststart(video_path: str, output_path: Optional[str] = None) -> bool:
    """
    Runs FFmpeg with -movflags +faststart -c copy to relocate the moov atom header
    to the beginning of the file for instant HTML5 web streaming.
    """
    if not os.path.exists(video_path):
        return False

    temp_output = output_path or f"{video_path}.faststart.mp4"
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-c", "copy",
            "-movflags", "+faststart",
            temp_output
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
            if output_path is None:
                os.replace(temp_output, video_path)
            logger.info(f"Faststart optimization succeeded for {video_path}")
            return True
        else:
            logger.warning(f"Faststart optimization failed for {video_path}: {result.stderr}")
            if output_path is None and os.path.exists(temp_output):
                try:
                    os.remove(temp_output)
                except OSError:
                    pass
            return False
    except Exception as e:
        logger.error(f"FFmpeg faststart error for {video_path}: {e}")
        if output_path is None and os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except OSError:
                pass
        return False

