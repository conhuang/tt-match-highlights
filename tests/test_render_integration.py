import unittest
from unittest.mock import MagicMock, patch
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

os.environ["DB_TYPE"] = "local"
os.environ["STORAGE_TYPE"] = "local"
os.environ["LOCAL_STORAGE_DIR"] = "storage_test_render"
os.environ["SQLITE_DB_PATH"] = "storage_test_render/metadata.db"

from app.main import app, db, storage
from app.models import Match, Event, RenderJob, RenderOptions
from app.render_adapter import execute_render_job, update_render_job_status
from fastapi.testclient import TestClient


class TestRenderIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        os.makedirs("storage_test_render", exist_ok=True)
        db._init_db()
        self.match_id = "test_render_match_789"
        self.match = Match(
            id=self.match_id,
            name="Render Integration Match",
            player1="Alice",
            player2="Bob",
            video_filename=f"{self.match_id}.mp4",
            events=[
                Event(start=1.0, end=5.0, winner="Alice", isHighlight=True, game=1),
                Event(start=6.0, end=10.0, winner="Bob", isHighlight=False, game=1)
            ]
        )
        db.create_match(self.match.model_dump())

    def tearDown(self):
        if os.path.exists("storage_test_render"):
            import shutil
            shutil.rmtree("storage_test_render")

    def test_validation_render_endpoint_errors(self):
        """Verify 400 validation error when match missing events or raw video."""
        # 1. Match with no events
        empty_match = Match(id="empty_match", name="Empty", player1="A", player2="B", video_filename="raw.mp4")
        db.create_match(empty_match.model_dump())

        res1 = self.client.post("/api/matches/empty_match/renders", json={"type": "full_match"})
        self.assertEqual(res1.status_code, 400)
        self.assertIn("without logged events", res1.json()["detail"])

        # 2. Match with no video
        no_vid_match = Match(id="no_vid", name="No Vid", player1="A", player2="B", events=[Event(start=0, end=1)])
        db.create_match(no_vid_match.model_dump())

        res2 = self.client.post("/api/matches/no_vid/renders", json={"type": "full_match"})
        self.assertEqual(res2.status_code, 400)
        self.assertIn("without an uploaded raw video", res2.json()["detail"])

    @patch("app.main.execute_render_job")
    def test_create_and_list_render_jobs(self, mock_execute_job):
        """Verify triggering render job creates entry in match.renders and queues background task."""
        payload = {
            "type": "full_match",
            "label": "Full Scored Match Test",
            "options": {
                "highlights_only": False,
                "include_scoreboard": True,
                "include_game_cards": True,
                "cpu_mode": True
            }
        }
        res = self.client.post(f"/api/matches/{self.match_id}/renders", json=payload)
        self.assertEqual(res.status_code, 202)
        job_json = res.json()

        render_id = job_json["id"]
        self.assertIsNotNone(render_id)
        self.assertEqual(job_json["status"], "rendering")
        self.assertEqual(job_json["options"]["include_scoreboard"], True)
        self.assertEqual(job_json["options"]["include_game_cards"], True)

        # Verify job is listed in GET /renders
        list_res = self.client.get(f"/api/matches/{self.match_id}/renders")
        self.assertEqual(list_res.status_code, 200)
        renders = list_res.json()
        self.assertTrue(any(r["id"] == render_id for r in renders))

        # Verify status endpoint
        status_res = self.client.get(f"/api/matches/{self.match_id}/renders/{render_id}/status")
        self.assertEqual(status_res.status_code, 200)
        self.assertEqual(status_res.json()["id"], render_id)

    def test_delete_render_job(self):
        """Verify DELETE /renders/{render_id} cleans up DB record and storage file."""
        job = RenderJob(
            id="job_to_delete",
            type="full_match",
            filename="job_to_delete.mp4",
            status="completed",
            progress=100
        )
        match_rec = db.get_match(self.match_id)
        match_obj = Match.model_validate(match_rec)
        match_obj.renders.append(job)
        db.create_match(match_obj.model_dump())

        # Seed mock render file in storage
        base_dir = getattr(storage, "base_dir", "storage_test_render")
        render_file = os.path.join(base_dir, "renders", "job_to_delete.mp4")
        os.makedirs(os.path.dirname(render_file), exist_ok=True)
        with open(render_file, "wb") as f:
            f.write(b"mock render content")

        del_res = self.client.delete(f"/api/matches/{self.match_id}/renders/job_to_delete")
        self.assertEqual(del_res.status_code, 200)

        # Verify job is gone from match.renders
        updated_rec = db.get_match(self.match_id)
        self.assertFalse(any(r["id"] == "job_to_delete" for r in updated_rec.get("renders", [])))
        # Verify file deleted from storage
        self.assertFalse(os.path.exists(render_file))

    def test_cancel_render_job(self):
        """Verify POST /renders/{render_id}/cancel sets status to failed/cancelled."""
        job = RenderJob(
            id="job_to_cancel",
            type="full_match",
            status="rendering",
            progress=25,
            stage="Encoding"
        )
        match_rec = db.get_match(self.match_id)
        match_obj = Match.model_validate(match_rec)
        match_obj.renders.append(job)
        db.create_match(match_obj.model_dump())

        # Call cancel endpoint
        cancel_res = self.client.post(f"/api/matches/{self.match_id}/renders/{job.id}/cancel")
        self.assertEqual(cancel_res.status_code, 200)
        self.assertEqual(cancel_res.json()["status"], "cancelling")

        # Verify DB status updated to failed/Cancelled
        status_res = self.client.get(f"/api/matches/{self.match_id}/renders/{job.id}/status")
        self.assertEqual(status_res.status_code, 200)
        self.assertEqual(status_res.json()["status"], "failed")
        self.assertEqual(status_res.json()["stage"], "Cancelled")


if __name__ == "__main__":
    unittest.main()
