import os
import shutil
from abc import ABC, abstractmethod
from typing import Optional

class StorageProvider(ABC):
    """
    Abstract Base Class for file storage operations.
    Supports local file system for dev and AWS S3 for production.
    """
    @abstractmethod
    def upload_file(self, local_path: str, remote_name: str) -> bool:
        pass

    @abstractmethod
    def upload_fileobj(self, file_obj, remote_name: str) -> bool:
        """Upload a file-like object directly (useful for streaming uploads)."""
        pass

    @abstractmethod
    def download_file(self, remote_name: str, local_path: str) -> bool:
        pass

    @abstractmethod
    def get_download_url(self, remote_name: str, expiration: int = 3600) -> str:
        """Generate a temporary URL for client browser playback."""
        pass

    @abstractmethod
    def delete_file(self, remote_name: str) -> bool:
        pass


class LocalStorageProvider(StorageProvider):
    """
    Local file system storage implementation.
    """
    def __init__(self, base_dir: str = "storage"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        # Create separate uploads and renders folders inside storage
        os.makedirs(os.path.join(base_dir, "uploads"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "renders"), exist_ok=True)

    def _get_local_path(self, remote_name: str) -> str:
        return os.path.join(self.base_dir, remote_name)

    def upload_file(self, local_path: str, remote_name: str) -> bool:
        dest = self._get_local_path(remote_name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(local_path, dest)
        return True

    def upload_fileobj(self, file_obj, remote_name: str) -> bool:
        dest = self._get_local_path(remote_name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file_obj, f)
        return True

    def download_file(self, remote_name: str, local_path: str) -> bool:
        src = self._get_local_path(remote_name)
        if os.path.exists(src):
            shutil.copyfile(src, local_path)
            return True
        return False

    def get_download_url(self, remote_name: str, expiration: int = 3600) -> str:
        # For local dev, route files through a static FastAPI mount
        # e.g., /static/videos/uploads/vytxeJKJygguct7vC6Lxw.mp4
        return f"/static/videos/{remote_name}"

    def delete_file(self, remote_name: str) -> bool:
        path = self._get_local_path(remote_name)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False


class S3StorageProvider(StorageProvider):
    """
    AWS S3 storage implementation.
    """
    def __init__(self, bucket_name: str):
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for S3 storage. Run 'pip install boto3' to install it."
            )
        self.s3_client = boto3.client("s3")
        self.bucket_name = bucket_name

    def upload_file(self, local_path: str, remote_name: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.s3_client.upload_file(local_path, self.bucket_name, remote_name)
            return True
        except ClientError:
            return False

    def upload_fileobj(self, file_obj, remote_name: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.s3_client.upload_fileobj(file_obj, self.bucket_name, remote_name)
            return True
        except ClientError:
            return False

    def download_file(self, remote_name: str, local_path: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.s3_client.download_file(self.bucket_name, remote_name, local_path)
            return True
        except ClientError:
            return False

    def get_download_url(self, remote_name: str, expiration: int = 3600) -> str:
        from botocore.exceptions import ClientError
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": remote_name},
                ExpiresIn=expiration
            )
            return url
        except ClientError:
            return ""

    def delete_file(self, remote_name: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=remote_name)
            return True
        except ClientError:
            return False


def get_storage_provider() -> StorageProvider:
    """
    Factory function returning the active Storage Provider.
    Reads STORAGE_TYPE environment variable (defaults to 'local').
    """
    storage_type = os.getenv("STORAGE_TYPE", "local").lower()
    
    if storage_type == "s3":
        bucket_name = os.getenv("S3_BUCKET_NAME", "tt-video-editor-storage")
        return S3StorageProvider(bucket_name=bucket_name)
    else:
        base_dir = os.getenv("LOCAL_STORAGE_DIR", "storage")
        return LocalStorageProvider(base_dir=base_dir)
