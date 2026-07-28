import unittest
from unittest.mock import MagicMock, patch
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

os.environ["DB_TYPE"] = "local"
os.environ["STORAGE_TYPE"] = "local"
os.environ["LOCAL_STORAGE_DIR"] = "storage_test_stream"

from app.storage import LocalStorageProvider, S3StorageProvider
from app.main import app, db, storage
from app.models import Match


class TestDirectS3Streaming(unittest.TestCase):
    def setUp(self):
        os.makedirs("storage_test_stream", exist_ok=True)
        db._init_db()
        self.match_id = "test_stream_match_456"
        self.match = Match(
            id=self.match_id,
            name="Direct Streaming Test",
            player1="Alice",
            player2="Bob",
            video_filename=f"{self.match_id}.mp4"
        )
        db.create_match(self.match.model_dump())

    def tearDown(self):
        if os.path.exists("metadata.db"):
            os.remove("metadata.db")
        if os.path.exists("storage_test_stream"):
            import shutil
            shutil.rmtree("storage_test_stream")

    def test_local_storage_provider_get_object_stream(self):
        """Verify LocalStorageProvider.get_object_stream returns valid range iterators."""
        provider = LocalStorageProvider(base_dir="storage_test_stream")
        remote_name = "uploads/sample.mp4"
        local_path = os.path.join("storage_test_stream", remote_name)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(b"0123456789" * 10)  # 100 bytes

        # Range request
        res = provider.get_object_stream(remote_name, range_header="bytes=0-49")
        self.assertIsNotNone(res)
        self.assertEqual(res["status_code"], 206)
        self.assertEqual(res["content_length"], 50)
        self.assertEqual(res["content_range"], "bytes 0-49/100")
        
        chunks = list(res["iter"])
        content = b"".join(chunks)
        self.assertEqual(content, b"0123456789" * 5)

    @patch("boto3.client")
    def test_s3_storage_provider_get_object_stream(self, mock_boto3):
        """Verify S3StorageProvider.get_object_stream fetches range objects directly from S3."""
        mock_s3 = MagicMock()
        mock_boto3.return_value = mock_s3

        mock_body = MagicMock()
        mock_body.iter_chunks.return_value = [b"chunk1", b"chunk2"]

        mock_s3.get_object.return_value = {
            "Body": mock_body,
            "ContentLength": 1000,
            "ContentRange": "bytes 0-999/5000",
            "ContentType": "video/mp4"
        }

        provider = S3StorageProvider(bucket_name="test-bucket")
        provider.s3_client = mock_s3

        res = provider.get_object_stream("uploads/video.mp4", range_header="bytes=0-999")

        self.assertIsNotNone(res)
        self.assertEqual(res["status_code"], 206)
        self.assertEqual(res["content_length"], 1000)
        self.assertEqual(res["content_range"], "bytes 0-999/5000")

        mock_s3.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="uploads/video.mp4",
            Range="bytes=0-999"
        )


if __name__ == "__main__":
    unittest.main()
