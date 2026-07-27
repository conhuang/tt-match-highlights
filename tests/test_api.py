import unittest
import sys
import os
from fastapi.testclient import TestClient

# Add src and root to path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# Force local testing database settings
os.environ["DB_TYPE"] = "local"
os.environ["STORAGE_TYPE"] = "local"
os.environ["LOCAL_STORAGE_DIR"] = "storage_test"

from app.main import app
from app.models import Match

class TestFastAPIBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Ensure test storage directory exists
        os.makedirs("storage_test", exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        # Clean up local test metadata database and test storage folder
        if os.path.exists("metadata.db"):
            os.remove("metadata.db")
        if os.path.exists("storage_test"):
            import shutil
            shutil.rmtree("storage_test")

    def test_full_match_crud_lifecycle(self):
        """
        Verify the complete CRUD lifecycle of a Match and its Event logs.
        """
        # 1. Create a Match
        match_data = {
            "name": "Championship Match",
            "player1": "Alice",
            "player2": "Bob"
        }
        create_res = self.client.post("/api/matches", json=match_data)
        self.assertEqual(create_res.status_code, 201)
        match_json = create_res.json()
        
        match_id = match_json["id"]
        self.assertIsNotNone(match_id)
        self.assertEqual(match_json["name"], "Championship Match")
        self.assertEqual(match_json["player1"], "Alice")
        self.assertEqual(match_json["player2"], "Bob")
        self.assertEqual(match_json["events"], [])

        # 2. List Matches (Verify our match exists in list)
        list_res = self.client.get("/api/matches")
        self.assertEqual(list_res.status_code, 200)
        matches = list_res.json()
        self.assertTrue(any(m["id"] == match_id for m in matches))

        # 3. Retrieve Single Match
        get_res = self.client.get(f"/api/matches/{match_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["id"], match_id)

        # 4. Update Match Events (Phase 2 Key Event Log)
        events_payload = {
            "events": [
                {
                    "start": 10.5,
                    "end": 15.0,
                    "winner": "Alice",
                    "timeout_player": None,
                    "isHighlight": True,
                    "game": 1,
                    "score_before": "0-0"
                },
                {
                    "start": 22.1,
                    "end": 28.5,
                    "winner": "Bob",
                    "timeout_player": "Alice",
                    "isHighlight": False,
                    "game": 1,
                    "score_before": "1-0"
                }
            ]
        }
        update_res = self.client.put(f"/api/matches/{match_id}", json=events_payload)
        self.assertEqual(update_res.status_code, 200)
        updated_match = update_res.json()
        
        # Verify events are saved correctly
        self.assertEqual(len(updated_match["events"]), 2)
        self.assertEqual(updated_match["events"][0]["winner"], "Alice")
        self.assertEqual(updated_match["events"][0]["isHighlight"], True)
        self.assertEqual(updated_match["events"][1]["winner"], "Bob")
        self.assertEqual(updated_match["events"][1]["timeout_player"], "Alice")

        # 5. Initialize Multipart Upload (Tracer Bullet S3/Local)
        init_payload = {
            "filename": "gameplay.mp4",
            "file_size": 120 * 1024 * 1024  # 120MB
        }
        init_res = self.client.post(f"/api/matches/{match_id}/upload/initialize", json=init_payload)
        self.assertEqual(init_res.status_code, 200)
        init_json = init_res.json()
        self.assertIsNotNone(init_json["upload_id"])
        # With 120MB and 50MB chunks, it should generate exactly 3 parts
        self.assertEqual(len(init_json["parts"]), 3)
        self.assertEqual(init_json["parts"][0]["PartNumber"], 1)

        # 6. Delete Match & Clean Up
        delete_res = self.client.delete(f"/api/matches/{match_id}")
        self.assertEqual(delete_res.status_code, 200)
        self.assertEqual(delete_res.json()["status"], "success")

        # 7. Verify GET returns 404 after deletion
        post_delete_res = self.client.get(f"/api/matches/{match_id}")
        self.assertEqual(post_delete_res.status_code, 404)

    def test_scoring_engine_auto_calculations(self):
        """
        Verify that the scoring engine auto-computes running scores,
        transitions game numbers, and implements deuce rules (win by 2).
        """
        # Create a match
        create_res = self.client.post("/api/matches", json={
            "name": "Scoring Test",
            "player1": "Alice",
            "player2": "Bob"
        })
        match_id = create_res.json()["id"]

        # 1. Test standard game transition (Alice wins 11-0)
        # We send 12 points where Alice wins all of them.
        events = []
        for i in range(12):
            events.append({
                "start": float(i * 10),
                "end": float(i * 10 + 5),
                "winner": "Alice",
                "isHighlight": False
            })

        update_res = self.client.put(f"/api/matches/{match_id}", json={"events": events})
        self.assertEqual(update_res.status_code, 200)
        result = update_res.json()["events"]

        # First point should start at 0-0 in Game 1
        self.assertEqual(result[0]["score_before"], "0-0")
        self.assertEqual(result[0]["game"], 1)

        # 11th point should start at 10-0 in Game 1
        self.assertEqual(result[10]["score_before"], "10-0")
        self.assertEqual(result[10]["game"], 1)

        # 12th point should start at 0-0 in Game 2 (because Alice won Game 1 11-0)
        self.assertEqual(result[11]["score_before"], "0-0")
        self.assertEqual(result[11]["game"], 2)

        # 2. Test Deuce / Win-by-Two rules
        # We simulate a 10-10 tie, followed by a 1-point lead (no win), then a 2-point lead (win).
        deuce_events = []
        t = 0
        # Alice wins 10 points, Bob wins 10 points
        for _ in range(10):
            deuce_events.append({"start": float(t), "end": float(t+1), "winner": "Alice"})
            t += 2
            deuce_events.append({"start": float(t), "end": float(t+1), "winner": "Bob"})
            t += 2
        
        # At this point, the score is 10-10.
        # Alice wins next point -> 11-10 (game should NOT transition yet)
        deuce_events.append({"start": float(t), "end": float(t+1), "winner": "Alice"})
        t += 2

        # Alice wins next point -> 12-10 (game should win!)
        deuce_events.append({"start": float(t), "end": float(t+1), "winner": "Alice"})
        t += 2

        # One more point to check if game 2 starts at 0-0
        deuce_events.append({"start": float(t), "end": float(t+1), "winner": "Bob"})

        update_res2 = self.client.put(f"/api/matches/{match_id}", json={"events": deuce_events})
        result2 = update_res2.json()["events"]

        # Check deuce state (point 20 in 0-indexed list is the 21st point, representing Alice's serve at 10-10)
        self.assertEqual(result2[20]["score_before"], "10-10")
        self.assertEqual(result2[20]["game"], 1)

        # Point 21 represents Alice's serve at 11-10 (no win yet)
        self.assertEqual(result2[21]["score_before"], "11-10")
        self.assertEqual(result2[21]["game"], 1)

        # Point 22 should start at 0-0 in Game 2 (because Alice won 12-10)
        self.assertEqual(result2[22]["score_before"], "0-0")
        self.assertEqual(result2[22]["game"], 2)

        # Clean up
        self.client.delete(f"/api/matches/{match_id}")

    def test_video_streaming_and_metadata(self):
        """
        Verify video stream endpoint with HTTP 206 Partial Content Range Headers.
        """
        # Create match
        create_res = self.client.post("/api/matches", json={
            "name": "Stream Test Match",
            "player1": "Alice",
            "player2": "Bob"
        })
        match_id = create_res.json()["id"]

        # Seed mock video file
        upload_dir = os.path.join("storage_test", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        video_file = os.path.join(upload_dir, f"{match_id}.mp4")
        mock_data = b"0123456789" * 100  # 1000 bytes
        with open(video_file, "wb") as f:
            f.write(mock_data)

        # Link video filename to match record
        self.client.put(f"/api/matches/{match_id}", json={"video_filename": f"{match_id}.mp4"})

        # 1. Test Stream Full Video (No Range Header)
        full_res = self.client.get(f"/api/matches/{match_id}/stream")
        self.assertEqual(full_res.status_code, 200)
        self.assertEqual(len(full_res.content), 1000)

        # 2. Test Stream Byte Range (HTTP 206 Partial Content)
        headers = {"range": "bytes=0-99"}
        range_res = self.client.get(f"/api/matches/{match_id}/stream", headers=headers)
        self.assertEqual(range_res.status_code, 206)
        self.assertEqual(len(range_res.content), 100)
        self.assertEqual(range_res.content, mock_data[:100])
        self.assertEqual(range_res.headers["Content-Range"], "bytes 0-99/1000")
        self.assertEqual(range_res.headers["Accept-Ranges"], "bytes")

        # Clean up
        self.client.delete(f"/api/matches/{match_id}")

    def test_dynamodb_float_serialization_regression(self):
        """
        Regression Test: Verify that Python floats in match metadata and event lists
        are converted to Decimal types for DynamoDB without throwing TypeError.
        """
        from decimal import Decimal
        from app.database import _to_dynamo_item, _from_dynamo_item

        raw_match_data = {
            "id": "regression_match_123",
            "fps": 29.97,
            "duration": 145.8,
            "events": [
                {"start": 10.5, "end": 15.2, "winner": "Alice"},
                {"start": 30.1, "end": 35.8, "winner": "Bob"}
            ]
        }

        # 1. Convert to DynamoDB item format
        dynamo_item = _to_dynamo_item(raw_match_data)
        
        # Assert floats are converted to Decimal
        self.assertIsInstance(dynamo_item["fps"], Decimal)
        self.assertIsInstance(dynamo_item["duration"], Decimal)
        self.assertIsInstance(dynamo_item["events"][0]["start"], Decimal)
        self.assertIsInstance(dynamo_item["events"][0]["end"], Decimal)

        # 2. Convert back to Python API response format
        restored = _from_dynamo_item(dynamo_item)
        self.assertIsInstance(restored["fps"], float)
        self.assertIsInstance(restored["duration"], float)
        self.assertEqual(restored["fps"], 29.97)
        self.assertEqual(restored["events"][0]["start"], 10.5)

if __name__ == "__main__":
    unittest.main()


