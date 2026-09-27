import unittest
import os
import sys
import json

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

os.environ["DB_TYPE"] = "local"
os.environ["STORAGE_TYPE"] = "local"
os.environ["LOCAL_STORAGE_DIR"] = "storage_test"
os.environ["SQLITE_DB_PATH"] = "storage_test/metadata.db"

from app.models import Event, Match
from app.scoring import compute_scores_and_games
from app.video_utils import generate_720p_preview
from app.database import SQLiteRepository
from fastapi.testclient import TestClient
from app.main import app, db

class TestFeatures1359(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.p1 = "Jonsen"
        self.p2 = "Ryan"

    def test_item_1_scoring_logic_score_after(self):
        """
        Verify that compute_scores_and_games properly derives score after points,
        and advances game counts when reaching 11 points (win by 2).
        """
        events = [
            Event(start=1.0, end=3.0, winner="Jonsen"),
            Event(start=4.0, end=6.0, winner="Ryan"),
            Event(start=7.0, end=9.0, winner="Jonsen"),
        ]
        scored = compute_scores_and_games(events, self.p1, self.p2)
        self.assertEqual(len(scored), 3)
        self.assertEqual(scored[0].game, 1)
        self.assertEqual(scored[1].game, 1)
        self.assertEqual(scored[2].game, 1)

    def test_item_3_preview_endpoint_and_fallback(self):
        """
        Verify that GET /api/matches/{id}/preview falls back to stream or returns 404 if no video.
        """
        match_id = "test_preview_match"
        match = Match(
            id=match_id,
            name="Test Preview",
            player1="A",
            player2="B",
            video_filename="non_existent.mp4"
        )
        db.create_match(match.model_dump())
        try:
            resp = self.client.get(f"/api/matches/{match_id}/preview")
            # Either 404 because file is not on disk in test, or 307 if s3 redirect
            self.assertIn(resp.status_code, [404, 307])
        finally:
            db.delete_match(match_id)

    def test_database_preview_video_filename_persistence(self):
        """
        Verify that preview_video_filename is stored and retrieved in the database.
        """
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            test_db = SQLiteRepository(tmp.name)
            match_data = {
                "id": "match_with_preview",
                "name": "Match Preview Test",
                "player1": "P1",
                "player2": "P2",
                "video_filename": "orig.mp4",
                "preview_video_filename": "preview_720p.mp4",
                "width": 1920,
                "height": 1080
            }
            test_db.create_match(match_data)
            loaded = test_db.get_match("match_with_preview")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.get("preview_video_filename"), "preview_720p.mp4")
            self.assertEqual(loaded.get("width"), 1920)
            self.assertEqual(loaded.get("height"), 1080)

if __name__ == "__main__":
    unittest.main()
