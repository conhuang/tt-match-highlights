import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.main import app, db, storage
from app.models import Match, AutoDetectJob
from app.detect_adapter import execute_auto_detect_job


class TestAutoDetectAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_user = {"email": "test@example.com", "authenticated": True}
        self.match_id = "test_detect_match_456"

        if hasattr(db, "_init_db"):
            db._init_db()

        self.match_data = {
            "id": self.match_id,
            "owner_username": "test@example.com",
            "name": "Auto Detect Test Match",
            "player1": "Player One",
            "player2": "Player Two",
            "first_server": "player1",
            "video_filename": "test_video.mp4",
            "duration": 120.0,
            "events": [],
            "renders": [],
            "auto_detect_job": None
        }
        db.create_match(self.match_data)
        from app.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: self.test_user

    def tearDown(self):
        app.dependency_overrides.clear()
        db.delete_match(self.match_id)

    def test_trigger_auto_detect_forbidden_user(self):
        """Verify another user cannot trigger auto-detect on a match they do not own."""
        from app.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: {"email": "stranger@example.com", "authenticated": True}
        resp = self.client.post(f"/api/matches/{self.match_id}/auto-detect")
        self.assertEqual(resp.status_code, 403)

    def test_trigger_auto_detect_missing_video(self):
        """Verify error returned if match has no uploaded video."""
        record = db.get_match(self.match_id)
        record["video_filename"] = None
        db.create_match(record)

        resp = self.client.post(f"/api/matches/{self.match_id}/auto-detect")
        self.assertEqual(resp.status_code, 400)

    @patch("app.detect_adapter.execute_auto_detect_job")
    def test_trigger_auto_detect_success_local(self, mock_exec):
        """Verify triggering auto-detect creates a queued job and returns it."""
        resp = self.client.post(
            f"/api/matches/{self.match_id}/auto-detect",
            json={"mode": "replace", "model": "gemini-2.5-flash"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "queued")
        self.assertEqual(data["progress"], 0)
        self.assertIn("id", data)

        # Verify match record in DB was updated
        record = db.get_match(self.match_id)
        self.assertIsNotNone(record.get("auto_detect_job"))
        self.assertEqual(record["auto_detect_job"]["id"], data["id"])

    @patch("boto3.client")
    def test_trigger_auto_detect_aws_batch_dispatch(self, mock_boto):
        """Verify AWS Batch submission when AWS_BATCH_JOB_QUEUE is configured."""
        mock_batch = MagicMock()
        mock_boto.return_value = mock_batch

        with patch.dict(os.environ, {
            "AWS_BATCH_JOB_QUEUE": "tt-test-queue",
            "AWS_BATCH_JOB_DEF": "tt-test-job-def",
            "AWS_REGION": "us-east-2"
        }):
            resp = self.client.post(f"/api/matches/{self.match_id}/auto-detect")
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(mock_batch.submit_job.called)
            call_kwargs = mock_batch.submit_job.call_args[1]
            self.assertEqual(call_kwargs["jobQueue"], "tt-test-queue")
            self.assertIn("scripts/run_gpu_detect_job.py", call_kwargs["containerOverrides"]["command"])

    def test_get_auto_detect_status(self):
        """Verify status polling endpoint returns the active job."""
        # Seed an active job
        job = AutoDetectJob(
            id="job_xyz",
            status="transcoding",
            progress=25,
            stage="Downscaling video to 720p..."
        )
        record = db.get_match(self.match_id)
        record["auto_detect_job"] = job.model_dump()
        db.create_match(record)

        resp = self.client.get(f"/api/matches/{self.match_id}/auto-detect/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], "job_xyz")
        self.assertEqual(data["status"], "transcoding")
        self.assertEqual(data["progress"], 25)

    def test_cancel_auto_detect(self):
        """Verify cancelling an active job."""
        job = AutoDetectJob(id="job_to_cancel", status="tracking", progress=50)
        record = db.get_match(self.match_id)
        record["auto_detect_job"] = job.model_dump()
        db.create_match(record)

        resp = self.client.post(f"/api/matches/{self.match_id}/auto-detect/cancel")
        self.assertEqual(resp.status_code, 200)

        # Verify DB updated
        updated = db.get_match(self.match_id)
        self.assertEqual(updated["auto_detect_job"]["status"], "cancelled")

    @patch("app.detect_adapter.transcode_to_720p")
    def test_execute_auto_detect_job_tracer(self, mock_transcode):
        """Verify execute_auto_detect_job runs transcode and populates events."""
        # Setup mock local video in storage
        local_base = getattr(storage, "base_dir", "storage")
        upload_dir = os.path.join(local_base, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        test_video_path = os.path.join(upload_dir, "test_video.mp4")
        with open(test_video_path, "wb") as f:
            f.write(b"dummy video content")

        def side_effect_transcode(in_path, out_path, target_height=720):
            with open(out_path, "wb") as pf:
                pf.write(b"dummy 720p proxy")
            return out_path

        mock_transcode.side_effect = side_effect_transcode

        try:
            execute_auto_detect_job(
                match_id=self.match_id,
                job_id="test_tracer_job",
                db_repo=db,
                storage_provider=storage,
                mode="replace"
            )

            # Verify match events were populated and job is completed
            updated = db.get_match(self.match_id)
            match = Match.model_validate(updated)

            self.assertIsNotNone(match.auto_detect_job)
            self.assertEqual(match.auto_detect_job.status, "completed")
            self.assertEqual(match.auto_detect_job.progress, 100)
            self.assertGreater(len(match.events), 0)

            # Verify that generated events have unassigned winner (winner is None)
            for event in match.events:
                self.assertIsNone(event.winner)
                self.assertGreater(event.end, event.start)

        finally:
            if os.path.exists(test_video_path):
                os.remove(test_video_path)
