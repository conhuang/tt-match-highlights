"""
Hardware-accelerated 720p Transcoding Utility.

Downscales high-resolution input video (1080p / 4K @ 60fps) to 720p (1280x720):
- NVIDIA GPU (AWS Spot g4dn.xlarge): Zero-copy NVDEC -> scale_cuda -> NVENC (150-250+ FPS)
- macOS (Apple Silicon): VideoToolbox hardware acceleration
- CPU Fallback: Standard libx264 with superfast preset
"""

import os
import sys
import subprocess
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger("ml.transcode")


def is_nvidia_gpu_available() -> bool:
    """Check if NVIDIA GPU and NVENC are available in current environment."""
    try:
        res = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False


def is_nvenc_ffmpeg_supported() -> bool:
    """Check if the installed FFmpeg binary supports h264_nvenc and scale_cuda."""
    try:
        res = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
        return "h264_nvenc" in res.stdout
    except Exception:
        return False


def build_transcode_720p_command(
    input_path: str,
    output_path: str,
    target_height: int = 720,
    force_encoder: Optional[str] = None
) -> Tuple[List[str], str]:
    """
    Construct the optimal FFmpeg command for downscaling video to 720p.

    Args:
        input_path: Source video path or S3 presigned streaming URL.
        output_path: Destination 720p MP4 file path.
        target_height: Target vertical resolution in pixels (default: 720).
        force_encoder: Override encoder ('nvenc', 'videotoolbox', 'libx264').

    Returns:
        Tuple of (command_arguments_list, encoder_used_string).
    """
    is_macos = sys.platform == "darwin"
    has_nvidia = is_nvidia_gpu_available() and is_nvenc_ffmpeg_supported()

    if force_encoder == "nvenc" or (force_encoder is None and has_nvidia):
        # Zero-Copy Full GPU Pipeline:
        # NVDEC hardware decoding into GPU VRAM -> scale_cuda on CUDA cores -> h264_nvenc encoding
        cmd = [
            "ffmpeg", "-y",
            "-hwaccel", "cuda",
            "-hwaccel_output_format", "cuda",
            "-i", input_path,
            "-vf", f"scale_cuda=-2:{target_height}",
            "-c:v", "h264_nvenc",
            "-preset", "p4",
            "-cq", "24",
            "-c:a", "aac",
            "-b:a", "128k",
            output_path
        ]
        return cmd, "h264_nvenc"

    elif force_encoder == "videotoolbox" or (force_encoder is None and is_macos):
        # Apple Silicon / macOS Hardware Acceleration
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", f"scale=-2:{target_height}",
            "-c:v", "h264_videotoolbox",
            "-b:v", "4000k",
            "-c:a", "aac",
            "-b:a", "128k",
            output_path
        ]
        return cmd, "h264_videotoolbox"

    else:
        # Standard CPU Fallback
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", f"scale=-2:{target_height}",
            "-c:v", "libx264",
            "-preset", "superfast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            output_path
        ]
        return cmd, "libx264"


def transcode_to_720p(
    input_path: str,
    output_path: str,
    target_height: int = 720,
    force_encoder: Optional[str] = None
) -> str:
    """
    Execute hardware-accelerated 720p transcoding.

    Args:
        input_path: Path to source video.
        output_path: Path to write 720p output video.
        target_height: Target vertical resolution (default: 720).
        force_encoder: Optional encoder override.

    Returns:
        Path to output file.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cmd, encoder = build_transcode_720p_command(input_path, output_path, target_height, force_encoder)
    logger.info(f"Transcoding {input_path} to 720p using {encoder}...")

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        # If NVENC failed (e.g. CUDA device busy or format unsupported), retry with CPU fallback
        if encoder == "h264_nvenc":
            logger.warning(f"NVENC transcode failed ({res.stderr[:200]}). Retrying with CPU libx264 fallback...")
            fallback_cmd, _ = build_transcode_720p_command(input_path, output_path, target_height, force_encoder="libx264")
            fallback_res = subprocess.run(fallback_cmd, capture_output=True, text=True)
            if fallback_res.returncode != 0:
                raise RuntimeError(f"FFmpeg CPU transcode failed: {fallback_res.stderr}")
        else:
            raise RuntimeError(f"FFmpeg transcode failed: {res.stderr}")

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"Transcode produced empty output file: {output_path}")

    logger.info(f"Successfully transcoded 720p video: {output_path} ({os.path.getsize(output_path)} bytes)")
    return output_path
