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


if __name__ == "__main__":
    unittest.main()
