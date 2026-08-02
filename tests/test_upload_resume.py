import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import shutil
import io
from fastapi import HTTPException

# Add src to sys.path to find the package and app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.storage import LocalStorageProvider, S3StorageProvider
from app.main import list_parts as list_parts_endpoint


class TestUploadResume(unittest.TestCase):
    def setUp(self):
        self.temp_dir = "tests/temp_storage_test"
        os.makedirs(self.temp_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_local_storage_provider_multipart_flow(self):
        """Verify list_parts and completion flow in LocalStorageProvider."""
        provider = LocalStorageProvider(base_dir=self.temp_dir)
        remote_name = "uploads/test_match.mp4"

        # 1. Initiate upload
        upload_id = provider.initiate_multipart_upload(remote_name)
        self.assertIsNotNone(upload_id)

        # 2. Initially list parts should be empty
        parts = provider.list_parts(remote_name, upload_id)
        self.assertEqual(len(parts), 0)

        # 3. Save chunks
        part1_data = b"Hello "
        part2_data = b"World!"
        provider.save_upload_part(upload_id, 1, io.BytesIO(part1_data))
        provider.save_upload_part(upload_id, 2, io.BytesIO(part2_data))

        # 4. List parts should now contain both parts
        parts = provider.list_parts(remote_name, upload_id)
        self.assertEqual(len(parts), 2)
        
        # Sort to verify contents regardless of OS listing order
        parts.sort(key=lambda x: x["PartNumber"])
        self.assertEqual(parts[0]["PartNumber"], 1)
        self.assertEqual(parts[1]["PartNumber"], 2)

        # 5. Complete multipart upload
        completed = provider.complete_multipart_upload(
            remote_name=remote_name,
            upload_id=upload_id,
            parts=[
                {"PartNumber": 1, "ETag": "etag-1"},
                {"PartNumber": 2, "ETag": "etag-2"}
            ]
        )
        self.assertTrue(completed)

        # 6. Verify final compiled file content
        final_file_path = os.path.join(self.temp_dir, remote_name)
        self.assertTrue(os.path.exists(final_file_path))
        with open(final_file_path, "rb") as f:
            content = f.read()
        self.assertEqual(content, b"Hello World!")

        # 7. List parts should now be empty (temp folder cleaned up)
        parts = provider.list_parts(remote_name, upload_id)
        self.assertEqual(len(parts), 0)

    @patch("boto3.client")
    def test_s3_storage_provider_list_parts_and_pagination(self, mock_boto3_client):
        """Verify list_parts logic and pagination in S3StorageProvider."""
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3

        # Configure S3 mock for two-page pagination
        mock_s3.list_parts.side_effect = [
            {
                "Parts": [
                    {"PartNumber": 1, "ETag": "etag1"},
                    {"PartNumber": 2, "ETag": "etag2"}
                ],
                "IsTruncated": True,
                "NextPartNumberMarker": 2
            },
            {
                "Parts": [
                    {"PartNumber": 3, "ETag": "etag3"}
                ],
                "IsTruncated": False
            }
        ]

        provider = S3StorageProvider(bucket_name="test-bucket")
        provider.s3_client = mock_s3 # Explicitly replace with mock client

        parts = provider.list_parts("uploads/video.mp4", "mock-upload-id")

        # Verify correct number of items returned
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[0]["PartNumber"], 1)
        self.assertEqual(parts[1]["PartNumber"], 2)
        self.assertEqual(parts[2]["PartNumber"], 3)

        # Verify list_parts was called twice with correct markers
        self.assertEqual(mock_s3.list_parts.call_count, 2)
        mock_s3.list_parts.assert_any_call(
            Bucket="test-bucket",
            Key="uploads/video.mp4",
            UploadId="mock-upload-id"
        )
        mock_s3.list_parts.assert_any_call(
            Bucket="test-bucket",
            Key="uploads/video.mp4",
            UploadId="mock-upload-id",
            PartNumberMarker=2
        )

    @patch("boto3.client")
    def test_s3_storage_provider_complete_sorting(self, mock_boto3_client):
        """Verify complete_multipart_upload sorts parts by PartNumber before calling S3."""
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3

        provider = S3StorageProvider(bucket_name="test-bucket")
        provider.s3_client = mock_s3

        # Pass parts out of order
        unsorted_parts = [
            {"PartNumber": 3, "ETag": "etag3"},
            {"PartNumber": 1, "ETag": "etag1"},
            {"PartNumber": 2, "ETag": "etag2"}
        ]

        provider.complete_multipart_upload(
            remote_name="uploads/video.mp4",
            upload_id="mock-upload-id",
            parts=unsorted_parts
        )

        # Verify complete_multipart_upload was called with sorted parts
        mock_s3.complete_multipart_upload.assert_called_once_with(
            Bucket="test-bucket",
            Key="uploads/video.mp4",
            UploadId="mock-upload-id",
            MultipartUpload={
                "Parts": [
                    {"PartNumber": 1, "ETag": "etag1"},
                    {"PartNumber": 2, "ETag": "etag2"},
                    {"PartNumber": 3, "ETag": "etag3"}
                ]
            }
        )

    @patch("app.main.storage")
    def test_list_parts_endpoint_success(self, mock_storage):
        """Verify list_parts FastAPI endpoint returns parts list on success."""
        mock_storage.list_parts.return_value = [
            {"PartNumber": 1, "ETag": "etag-1"}
        ]

        # Call endpoint function directly
        response = list_parts_endpoint(
            match_id="test_match_id",
            upload_id="mock_upload_id",
            original_filename="match_video.mp4"
        )

        self.assertEqual(response, {"parts": [{"PartNumber": 1, "ETag": "etag-1"}]})
        mock_storage.list_parts.assert_called_once_with(
            remote_name="uploads/admin/test_match_id.mp4",
            upload_id="mock_upload_id"
        )

    @patch("app.main.storage")
    def test_list_parts_endpoint_error_propagation(self, mock_storage):
        """Verify list_parts endpoint captures and bubbles up storage provider errors."""
        mock_storage.list_parts.side_effect = Exception("AWS S3 AccessDenied or ConnectionError")

        with self.assertRaises(HTTPException) as context:
            list_parts_endpoint(
                match_id="test_match_id",
                upload_id="mock_upload_id",
                original_filename="match_video.mp4"
            )

        # Check HTTP exception details
        self.assertEqual(context.exception.status_code, 500)
        self.assertIn("Failed to query uploaded parts: AWS S3 AccessDenied", context.exception.detail)


if __name__ == "__main__":
    unittest.main()
