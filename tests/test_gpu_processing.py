import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.main import app, db, storage
from app.models import Match, Event, RenderJob, RenderOptions

class TestGPUProcessing(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_user = {"email": "test@example.com", "authenticated": True}
        
        # Seed test match record
        self.match_id = "gpu_test_match_123"
        self.match_data = {
            "id": self.match_id,
            "owner_username": "test@example.com",
            "name": "GPU Render Test",
            "player1": "Player A",
            "player2": "Player B",
            "first_server": "player1",
            "created_at": "2026-08-06T00:00:00Z",
            "video_filename": "test_raw_video.mp4",
            "events": [
                {
                    "start": 5.0,
                    "end": 10.0,
                    "winner": "Player A",
                    "isHighlight": True,
                    "game": 1
                }
            ],
            "renders": []
        }
        db.create_match(self.match_data)

    def tearDown(self):
        db.delete_match(self.match_id)

    @patch("app.main.get_current_user")
    @patch("boto3.client")
    def test_aws_batch_job_submission(self, mock_boto_client, mock_get_user):
        """Verify that when AWS_BATCH_JOB_QUEUE is set, create_render_job dispatches to AWS Batch."""
        mock_get_user.return_value = self.test_user
        mock_batch = MagicMock()
        mock_boto_client.return_value = mock_batch

        with patch.dict(os.environ, {
            "AWS_BATCH_JOB_QUEUE": "test-gpu-queue",
            "AWS_BATCH_JOB_DEF": "test-gpu-def",
            "STORAGE_TYPE": "s3",
            "S3_BUCKET_NAME": "test-bucket",
            "DB_TYPE": "dynamodb",
            "DYNAMODB_TABLE_NAME": "test-table"
        }):
            response = self.client.post(
                f"/api/matches/{self.match_id}/renders",
                json={
                    "type": "highlights",
                    "label": "GPU Highlights Test",
                    "options": {"highlights_only": True}
                }
            )

            self.assertEqual(response.status_code, 202)
            res_data = response.json()
            self.assertEqual(res_data["status"], "rendering")

            # Verify submit_job call on AWS Batch client
            mock_batch.submit_job.assert_called_once()
            _, kwargs = mock_batch.submit_job.call_args
            self.assertEqual(kwargs["jobQueue"], "test-gpu-queue")
            self.assertEqual(kwargs["jobDefinition"], "test-gpu-def")

            # Verify environment variables passed to GPU worker container
            env_vars = {item["name"]: item["value"] for item in kwargs["containerOverrides"]["environment"]}
            self.assertEqual(env_vars["MATCH_ID"], self.match_id)
            self.assertEqual(env_vars["RENDER_ID"], res_data["id"])
            self.assertEqual(env_vars["STORAGE_TYPE"], "s3")
            self.assertEqual(env_vars["S3_BUCKET_NAME"], "test-bucket")

    @patch("app.render_adapter.execute_render_job")
    def test_gpu_worker_script_execution(self, mock_execute_job):
        """Verify standalone scripts/run_gpu_render_job.py parses env vars and calls execute_render_job."""
        from scripts.run_gpu_render_job import main as gpu_main

        with patch.dict(os.environ, {"MATCH_ID": self.match_id, "RENDER_ID": "render_456"}):
            gpu_main()
            mock_execute_job.assert_called_once()
            _, kwargs = mock_execute_job.call_args
            self.assertEqual(kwargs["match_id"], self.match_id)
            self.assertEqual(kwargs["render_id"], "render_456")

    @patch("app.main.get_current_user")
    @patch("app.main.execute_render_job")
    def test_gpu_fallback_to_local_background_thread(self, mock_execute, mock_get_user):
        """Verify that when AWS_BATCH_JOB_QUEUE is unset, rendering falls back gracefully to background thread."""
        mock_get_user.return_value = self.test_user

        with patch.dict(os.environ, {}, clear=True):
            response = self.client.post(
                f"/api/matches/{self.match_id}/renders",
                json={
                    "type": "full_match",
                    "label": "Local Fallback Test",
                    "options": {"highlights_only": False}
                }
            )

            self.assertEqual(response.status_code, 202)
            res_data = response.json()
            self.assertEqual(res_data["status"], "rendering")

if __name__ == "__main__":
    unittest.main()
