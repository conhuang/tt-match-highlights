"""
Unit tests for 720p video transcoding utilities.
"""

import os
import sys

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from tt_video_editor.ml.transcode import build_transcode_720p_command


def test_build_transcode_nvenc_command():
    """Verify zero-copy NVDEC -> scale_cuda -> NVENC FFmpeg pipeline arguments."""
    cmd, encoder = build_transcode_720p_command(
        input_path="input.mp4",
        output_path="output_720p.mp4",
        target_height=720,
        force_encoder="nvenc"
    )

    assert encoder == "h264_nvenc"
    assert "-hwaccel" in cmd
    assert "cuda" in cmd
    assert "-hwaccel_output_format" in cmd
    assert "scale_cuda=-2:720" in cmd
    assert "h264_nvenc" in cmd
    assert "-preset" in cmd
    assert "p4" in cmd
    assert "output_720p.mp4" in cmd


def test_build_transcode_videotoolbox_command():
    """Verify macOS VideoToolbox hardware encoder command."""
    cmd, encoder = build_transcode_720p_command(
        input_path="input.mp4",
        output_path="output_720p.mp4",
        target_height=720,
        force_encoder="videotoolbox"
    )

    assert encoder == "h264_videotoolbox"
    assert "scale=-2:720" in cmd
    assert "h264_videotoolbox" in cmd


def test_build_transcode_libx264_command():
    """Verify CPU fallback encoder command."""
    cmd, encoder = build_transcode_720p_command(
        input_path="input.mp4",
        output_path="output_720p.mp4",
        target_height=720,
        force_encoder="libx264"
    )

    assert encoder == "libx264"
    assert "scale=-2:720" in cmd
    assert "superfast" in cmd
