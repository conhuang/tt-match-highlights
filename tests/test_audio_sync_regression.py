import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import json

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.models import Match, RenderJob, RenderOptions
from app.video_utils import extract_video_metadata
from app.render_adapter import execute_render_job


class TestAudioSyncRegression(unittest.TestCase):
    @patch("subprocess.run")
    @patch("os.path.exists", return_value=True)
    def test_extract_video_metadata_unrounded_fps(self, mock_exists, mock_subprocess):
        """Verify extract_video_metadata preserves full floating-point precision for 59.94 / 29.97 FPS NTSC streams."""
        ffprobe_output = {
            "streams": [
                {
                    "r_frame_rate": "60000/1001",
                    "duration": "120.5",
                    "width": 1920,
                    "height": 1080
                }
            ]
        }
        mock_subprocess.return_value = MagicMock(returncode=0, stdout=json.dumps(ffprobe_output))

        meta = extract_video_metadata("/dummy/path/match.mp4")
        expected_fps = 60000.0 / 1001.0
        self.assertAlmostEqual(meta["fps"], expected_fps, places=8)
        self.assertNotEqual(meta["fps"], round(expected_fps, 2))

    @patch("subprocess.Popen")
    @patch("subprocess.run")
    def test_render_adapter_probes_exact_r_frame_rate_and_sample_rate(self, mock_run, mock_popen):
        """Verify execute_render_job probes r_frame_rate directly and enforces 48000 Hz audio sample rate."""
        # Setup ffprobe mocks for stream metadata inspection
        def side_effect_run(cmd, *args, **kwargs):
            mock_res = MagicMock()
            mock_res.returncode = 0
            cmd_str = " ".join(cmd)
            if "r_frame_rate" in cmd_str:
                mock_res.stdout = json.dumps({
                    "streams": [{
                        "r_frame_rate": "60000/1001",
                        "width": 1920,
                        "height": 1080
                    }]
                })
            elif "color_space" in cmd_str:
                mock_res.stdout = "bt709,bt709,bt709"
            else:
                mock_res.stdout = ""
            return mock_res

        mock_run.side_effect = side_effect_run

        mock_process = MagicMock()
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        match_id = "match_audio_sync_test"
        render_id = "render_audio_sync_test"

        test_match = Match(
            id=match_id,
            name="Audio Sync Regression Test",
            player1="Player A",
            player2="Player B",
            video_filename=f"{match_id}.mp4",
            events=[
                {"start": 0.0, "end": 5.0, "winner": "Player A", "game": 1, "isHighlight": True}
            ],
            renders=[
                RenderJob(
                    id=render_id,
                    type="full_match",
                    options=RenderOptions(include_scoreboard=True, include_game_cards=True),
                    status="rendering",
                    progress=0,
                    stage="Queued"
                )
            ]
        )

        mock_db = MagicMock()
        mock_db.get_match.return_value = test_match.model_dump()

        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_storage = MagicMock()
            mock_storage.bucket_name = None
            mock_storage.base_dir = tmpdir

            # Create dummy raw video file to bypass download check
            raw_file = os.path.join(tmpdir, f"uploads/{match_id}.mp4")
            os.makedirs(os.path.dirname(raw_file), exist_ok=True)
            with open(raw_file, "wb") as f:
                f.write(b"dummy")

            execute_render_job(match_id, render_id, mock_db, mock_storage)

        # Inspect subprocess ffmpeg commands executed
        ffmpeg_cmds = [call_item[0][0] for call_item in mock_popen.call_args_list if call_item[0][0][0] == "ffmpeg"]
        self.assertTrue(len(ffmpeg_cmds) > 0)

        expected_fps_str = str(60000.0 / 1001.0)
        for cmd in ffmpeg_cmds:
            if "-f" in cmd and "concat" in cmd:
                continue
            # Ensure -r matches the exact probed FPS string
            self.assertIn("-r", cmd)
            r_idx = cmd.index("-r")
            self.assertEqual(cmd[r_idx + 1], expected_fps_str)

            # Ensure -ar 48000 is explicitly enforced for audio alignment
            self.assertIn("-ar", cmd)
            ar_idx = cmd.index("-ar")
            self.assertEqual(cmd[ar_idx + 1], "48000")

    def test_build_ffmpeg_card_cmd(self):
        from app.render_adapter import build_ffmpeg_card_cmd
        cmd = build_ffmpeg_card_cmd(
            card_path="/tmp/card.png",
            duration=2.0,
            width=1920,
            height=1080,
            encoder="libx264",
            encoder_opts=["-preset", "superfast"],
            color_primaries="bt709",
            color_trc="bt709",
            color_space="bt709",
            output_fps="59.94005994005994",
            output_path="/tmp/card.mp4"
        )
        self.assertEqual(cmd[0], "ffmpeg")
        self.assertIn("-ar", cmd)
        self.assertEqual(cmd[cmd.index("-ar") + 1], "48000")
        self.assertIn("-r", cmd)
        self.assertEqual(cmd[cmd.index("-r") + 1], "59.94005994005994")
        self.assertEqual(cmd[-1], "/tmp/card.mp4")

    def test_build_ffmpeg_clip_cmd(self):
        from app.render_adapter import build_ffmpeg_clip_cmd
        cmd = build_ffmpeg_clip_cmd(
            start_time=10.0,
            end_time=15.5,
            video_input_source="/tmp/input.mp4",
            overlay_path="/tmp/overlay.png",
            width=1920,
            height=1080,
            encoder="libx264",
            encoder_opts=["-preset", "superfast"],
            color_primaries="bt709",
            color_trc="bt709",
            color_space="bt709",
            output_fps="59.94005994005994",
            output_path="/tmp/clip.mp4"
        )
        self.assertEqual(cmd[0], "ffmpeg")
        self.assertIn("-ss", cmd)
        self.assertEqual(cmd[cmd.index("-ss") + 1], "10.0")
        self.assertIn("-to", cmd)
        self.assertEqual(cmd[cmd.index("-to") + 1], "15.5")
        self.assertIn("-ar", cmd)
        self.assertEqual(cmd[cmd.index("-ar") + 1], "48000")

    def test_build_ffmpeg_concat_cmd(self):
        from app.render_adapter import build_ffmpeg_concat_cmd
        cmd = build_ffmpeg_concat_cmd("/tmp/concat_list.txt", "/tmp/final.mp4", color_primaries="bt709", color_trc="bt709", color_space="bt709")
        self.assertEqual(cmd[0], "ffmpeg")
        self.assertIn("-f", cmd)
        self.assertEqual(cmd[cmd.index("-f") + 1], "concat")
        self.assertIn("-bsf:v", cmd)
        self.assertEqual(cmd[cmd.index("-bsf:v") + 1], "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1")
        self.assertIn("-color_primaries", cmd)
        self.assertEqual(cmd[cmd.index("-color_primaries") + 1], "bt709")
        self.assertIn("-color_trc", cmd)
        self.assertEqual(cmd[cmd.index("-color_trc") + 1], "bt709")
        self.assertIn("-colorspace", cmd)
        self.assertEqual(cmd[cmd.index("-colorspace") + 1], "bt709")
        self.assertEqual(cmd[-1], "/tmp/final.mp4")

    def test_get_nclc_codes(self):
        from app.render_adapter import get_nclc_codes
        cp, ct, cs = get_nclc_codes("bt709", "bt709", "bt709")
        self.assertEqual((cp, ct, cs), (1, 1, 1))

        cp_hdr, ct_hdr, cs_hdr = get_nclc_codes("bt2020", "arib-std-b67", "bt2020nc")
        self.assertEqual((cp_hdr, ct_hdr, cs_hdr), (9, 18, 9))

    @patch("subprocess.run")
    def test_probe_video_stream_info_zero_division_fps(self, mock_run):
        """Verify probe_video_stream_info handles 0/0 division by zero in r_frame_rate gracefully."""
        from app.render_adapter import probe_video_stream_info
        mock_res = MagicMock(returncode=0)
        mock_res.stdout = json.dumps({
            "streams": [{
                "r_frame_rate": "0/0",
                "width": 1920,
                "height": 1080
            }]
        })
        mock_run.return_value = mock_res

        info = probe_video_stream_info("/tmp/dummy.mp4", default_fps=29.97)
        self.assertEqual(info["output_fps"], "29.97")

    @patch("subprocess.run")
    def test_probe_video_stream_info_odd_dimensions_rescaling(self, mock_run):
        """Verify 4K / odd dimensions are capped at 1080p and rounded to even numbers for H.264 compatibility."""
        from app.render_adapter import probe_video_stream_info
        mock_res = MagicMock(returncode=0)
        mock_res.stdout = json.dumps({
            "streams": [{
                "r_frame_rate": "60/1",
                "width": 3840,
                "height": 2160
            }]
        })
        mock_run.return_value = mock_res

        info = probe_video_stream_info("/tmp/dummy.mp4")
        self.assertEqual(info["width"], 1920)
        self.assertEqual(info["height"], 1080)
        self.assertEqual(info["width"] % 2, 0)
        self.assertEqual(info["height"] % 2, 0)

    @patch("subprocess.run")
    def test_probe_video_stream_info_hdr_detection(self, mock_run):
        """Verify HDR video transfer characteristics (arib-std-b67 / HLG) set is_hdr to True."""
        from app.render_adapter import probe_video_stream_info
        mock_res = MagicMock(returncode=0)
        mock_res.stdout = json.dumps({
            "streams": [{
                "r_frame_rate": "60/1",
                "width": 1920,
                "height": 1080,
                "color_space": "bt2020nc",
                "color_transfer": "arib-std-b67",
                "color_primaries": "bt2020"
            }]
        })
        mock_run.return_value = mock_res

        info = probe_video_stream_info("/tmp/dummy.mp4")
        self.assertTrue(info["is_hdr"])
        self.assertEqual(info["color_space"], "bt2020nc")

    @patch("subprocess.run", side_effect=RuntimeError("ffprobe failure"))
    def test_probe_video_stream_info_ffprobe_failure(self, mock_run):
        """Verify probe_video_stream_info falls back to default width, height, and FPS if ffprobe fails."""
        from app.render_adapter import probe_video_stream_info
        info = probe_video_stream_info("/tmp/dummy.mp4", default_width=1280, default_height=720, default_fps=25.0)
        self.assertEqual(info["width"], 1280)
        self.assertEqual(info["height"], 720)
        self.assertEqual(info["output_fps"], "25.0")

    def test_build_ffmpeg_clip_cmd_without_overlay(self):
        """Verify build_ffmpeg_clip_cmd constructs simpler filter graph when overlay_path is None."""
        from app.render_adapter import build_ffmpeg_clip_cmd
        cmd = build_ffmpeg_clip_cmd(
            start_time=5.0,
            end_time=12.0,
            video_input_source="/tmp/input.mp4",
            overlay_path=None,
            width=1920,
            height=1080,
            encoder="libx264",
            encoder_opts=["-preset", "superfast"],
            color_primaries="bt709",
            color_trc="bt709",
            color_space="bt709",
            output_fps="30",
            output_path="/tmp/clip.mp4"
        )
        self.assertEqual(cmd[cmd.index("-filter_complex") + 1], "scale=1920:1080[vscaled]")
        self.assertEqual(cmd[cmd.index("-map") + 1], "[vscaled]")


if __name__ == "__main__":
    unittest.main()
