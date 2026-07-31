import unittest
from unittest.mock import MagicMock, patch
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.models import Match, RenderJob, RenderOptions
from app.render_adapter import execute_render_job
from app.storage import S3StorageProvider


class TestS3StreamingRenderAdapter(unittest.TestCase):
    @patch("subprocess.run")
    def test_execute_render_job_uses_s3_streaming_url(self, mock_subprocess):
        """Verify execute_render_job generates presigned S3 URL and sets stage text for S3 mode."""
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="bt709,bt709,bt709")

        # Mock DB repo
        mock_db = MagicMock()
        match_id = "match_s3_test_123"
        render_id = "render_s3_test_456"

        test_match = Match(
            id=match_id,
            name="S3 Streaming Test Match",
            player1="Player 1",
            player2="Player 2",
            video_filename=f"{match_id}.mp4",
            events=[
                {"start": 1.0, "end": 3.0, "winner": "Player 1", "game": 1, "isHighlight": True}
            ],
            renders=[
                RenderJob(
                    id=render_id,
                    type="highlights",
                    options=RenderOptions(highlights_only=True),
                    status="rendering",
                    progress=0,
                    stage="Queued"
                )
            ]
        )

        mock_db.get_match.return_value = test_match.model_dump()

        # Mock S3 Storage Provider
        mock_storage = MagicMock(spec=S3StorageProvider)
        mock_storage.bucket_name = "tt-video-editor-storage-test"
        mock_storage.get_download_url.return_value = "https://tt-video-editor-storage-test.s3.us-east-2.amazonaws.com/uploads/match_s3_test_123.mp4?presigned=true"

        with patch.dict(os.environ, {"STORAGE_TYPE": "s3"}):
            execute_render_job(match_id, render_id, mock_db, mock_storage)

        # Verify S3 presigned URL was fetched
        mock_storage.get_download_url.assert_called_once_with("uploads/match_s3_test_123.mp4", expiration=7200)

        # Verify DB updates included 'Streaming clips directly from S3'
        saved_calls = mock_db.create_match.call_args_list
        self.assertTrue(len(saved_calls) > 0)
        
        stages_updated = []
        for call_item in saved_calls:
            match_arg = call_item[0][0]
            for r in match_arg.get("renders", []):
                stages_updated.append(r.get("stage"))

        self.assertIn("Streaming clips directly from S3 (0s download wait)", stages_updated)


if __name__ == "__main__":
    unittest.main()
