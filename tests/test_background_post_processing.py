import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src and root to sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

os.environ["DB_TYPE"] = "local"
os.environ["STORAGE_TYPE"] = "local"
os.environ["LOCAL_STORAGE_DIR"] = "storage_test_bg"
os.environ["SQLITE_DB_PATH"] = "storage_test_bg/metadata.db"

from app.main import process_post_upload_tasks, complete_multipart, MultipartComplete, db
from app.models import Match


class TestBackgroundPostProcessing(unittest.TestCase):
    def setUp(self):
        os.makedirs("storage_test_bg", exist_ok=True)
        db._init_db()
        self.match_id = "test_bg_match_123"
        # Seed a match in db
        self.match = Match(
            id=self.match_id,
            name="Background Task Match Test",
            player1="Player 1",
            player2="Player 2"
        )
        db.create_match(self.match.model_dump())

    def tearDown(self):
        if os.path.exists("storage_test_bg"):
            import shutil
            shutil.rmtree("storage_test_bg")

    @patch("app.video_utils.extract_video_metadata")
    @patch("app.video_utils.optimize_video_for_faststart")
    def test_process_post_upload_tasks_updates_metadata(self, mock_faststart, mock_extract):
        """Verify process_post_upload_tasks runs faststart, extracts metadata, and updates DB."""
        mock_faststart.return_value = True
        mock_extract.return_value = {
            "fps": 60.0,
            "duration": 120.5,
            "width": 1920,
            "height": 1080
        }

        # Create dummy file
        local_path = os.path.join("storage_test_bg", "uploads", f"{self.match_id}.mp4")
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(b"dummy video content")

        # Run background task
        process_post_upload_tasks(
            match_id=self.match_id,
            remote_path=f"uploads/{self.match_id}.mp4",
            local_file_path=local_path
        )

        # Verify faststart and extract_video_metadata were called
        mock_faststart.assert_called_once_with(local_path)
        mock_extract.assert_called_once_with(local_path)

        # Verify DB record was updated with metadata
        updated_record = db.get_match(self.match_id)
        self.assertEqual(updated_record["fps"], 60.0)
        self.assertEqual(updated_record["duration"], 120.5)
        self.assertEqual(updated_record["width"], 1920)
        self.assertEqual(updated_record["height"], 1080)

    @patch("app.main.storage")
    def test_complete_multipart_queues_background_task(self, mock_storage):
        """Verify complete_multipart schedules post-processing on background_tasks."""
        mock_storage.complete_multipart_upload.return_value = True
        mock_storage.base_dir = "storage_test_bg"

        mock_bg_tasks = MagicMock()

        complete_data = MultipartComplete(
            upload_id="mock_upload_id",
            original_filename="sample.mp4",
            parts=[{"PartNumber": 1, "ETag": "etag1"}]
        )

        response = complete_multipart(
            match_id=self.match_id,
            complete_data=complete_data,
            background_tasks=mock_bg_tasks
        )

        self.assertEqual(response["status"], "upload_successful")
        self.assertEqual(response["video_filename"], f"{self.match_id}.mp4")

        # Verify background_tasks.add_task was called with process_post_upload_tasks
        mock_bg_tasks.add_task.assert_called_once()
        args = mock_bg_tasks.add_task.call_args[0]
        self.assertEqual(args[0], process_post_upload_tasks)
        self.assertEqual(args[1], self.match_id)


if __name__ == "__main__":
    unittest.main()
