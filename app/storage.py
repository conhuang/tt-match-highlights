import os
import shutil
import uuid
from abc import ABC, abstractmethod
from typing import Optional, List, Dict

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

    @abstractmethod
    def get_object_stream(self, remote_name: str, range_header: Optional[str] = None) -> Optional[Dict]:
        """Fetches a stream handle or iterator directly from storage for range streaming."""
        pass

    # --- Multipart Upload Methods ---
    @abstractmethod
    def initiate_multipart_upload(self, remote_name: str) -> str:
        """Starts a multipart upload and returns the upload ID."""
        pass

    @abstractmethod
    def generate_presigned_upload_part_url(self, remote_name: str, upload_id: str, part_number: int) -> str:
        """Generates the URL where the browser can upload a specific chunk."""
        pass

    @abstractmethod
    def complete_multipart_upload(self, remote_name: str, upload_id: str, parts: List[Dict]) -> bool:
        """Combines all uploaded parts into the final file."""
        pass

    @abstractmethod
    def abort_multipart_upload(self, remote_name: str, upload_id: str) -> bool:
        """Cancels the upload and deletes all uploaded temporary chunks."""
        pass

    @abstractmethod
    def save_upload_part(self, upload_id: str, part_number: int, file_obj) -> bool:
        """Saves a chunk to temporary storage (Only used in local development mode)."""
        pass

    @abstractmethod
    def list_parts(self, remote_name: str, upload_id: str) -> List[Dict]:
        """Lists already uploaded parts for an active multipart upload."""
        pass


class LocalStorageProvider(StorageProvider):
    """
    Local file system storage implementation.
    """
    def __init__(self, base_dir: str = "storage"):
        self.base_dir = base_dir
        self.temp_dir = os.path.join(base_dir, "temp_uploads")
        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(os.path.join(base_dir, "uploads"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "renders"), exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

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
        return f"/static/videos/{remote_name}"

    def delete_file(self, remote_name: str) -> bool:
        path = self._get_local_path(remote_name)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    # --- Multipart Local Mock ---
    def initiate_multipart_upload(self, remote_name: str, content_type: str = "video/mp4") -> str:
        upload_id = str(uuid.uuid4())
        upload_dir = os.path.join(self.temp_dir, upload_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save a reference mapping of remote name to file path in the temp folder
        with open(os.path.join(upload_dir, "remote_name.txt"), "w") as f:
            f.write(remote_name)
            
        return upload_id

    def generate_presigned_upload_part_url(self, remote_name: str, upload_id: str, part_number: int) -> str:
        # Direct local client uploads to a server-proxy route
        return f"/api/matches/upload/part?upload_id={upload_id}&part_number={part_number}"

    def save_upload_part(self, upload_id: str, part_number: int, file_obj) -> bool:
        upload_dir = os.path.join(self.temp_dir, upload_id)
        if not os.path.exists(upload_dir):
            return False
        
        part_file = os.path.join(upload_dir, str(part_number))
        with open(part_file, "wb") as f:
            shutil.copyfileobj(file_obj, f)
        return True

    def complete_multipart_upload(self, remote_name: str, upload_id: str, parts: List[Dict]) -> bool:
        upload_dir = os.path.join(self.temp_dir, upload_id)
        if not os.path.exists(upload_dir):
            return False

        final_dest = self._get_local_path(remote_name)
        os.makedirs(os.path.dirname(final_dest), exist_ok=True)

        # Sort parts by their part number to assemble chronologically
        sorted_parts = sorted(parts, key=lambda x: x["PartNumber"])

        with open(final_dest, "wb") as outfile:
            for part in sorted_parts:
                part_num = part["PartNumber"]
                part_file = os.path.join(upload_dir, str(part_num))
                if os.path.exists(part_file):
                    with open(part_file, "rb") as infile:
                        shutil.copyfileobj(infile, outfile)
                else:
                    return False
        
        # Clean up temporary parts folder
        shutil.rmtree(upload_dir)
        return True

    def abort_multipart_upload(self, remote_name: str, upload_id: str) -> bool:
        upload_dir = os.path.join(self.temp_dir, upload_id)
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir)
            return True
        return False

    def list_parts(self, remote_name: str, upload_id: str) -> List[Dict]:
        upload_dir = os.path.join(self.temp_dir, upload_id)
        if not os.path.exists(upload_dir):
            return []
        parts = []
        for name in os.listdir(upload_dir):
            if name.isdigit():
                parts.append({
                    "PartNumber": int(name),
                    "ETag": f'"mock-etag-{name}"'
                })
        return parts

    def get_object_stream(self, remote_name: str, range_header: Optional[str] = None) -> Optional[Dict]:
        """
        Local file system stream generator supporting byte-range requests.
        """
        local_path = self._get_local_path(remote_name)
        if not os.path.exists(local_path):
            return None
            
        file_size = os.path.getsize(local_path)
        if range_header:
            range_val = range_header.replace("bytes=", "").split("-")
            start = int(range_val[0]) if range_val[0] else 0
            end = int(range_val[1]) if len(range_val) > 1 and range_val[1] else file_size - 1
            end = min(end, file_size - 1)
            chunk_size = (end - start) + 1

            def iterfile():
                with open(local_path, "rb") as f:
                    f.seek(start)
                    bytes_left = chunk_size
                    while bytes_left > 0:
                        read_len = min(512 * 1024, bytes_left)
                        data = f.read(read_len)
                        if not data:
                            break
                        bytes_left -= len(data)
                        yield data

            return {
                "iter": iterfile(),
                "content_length": chunk_size,
                "content_range": f"bytes {start}-{end}/{file_size}",
                "content_type": "video/mp4",
                "status_code": 206
            }
        else:
            def iterfile_full():
                with open(local_path, "rb") as f:
                    while True:
                        data = f.read(512 * 1024)
                        if not data:
                            break
                        yield data
            return {
                "iter": iterfile_full(),
                "content_length": file_size,
                "content_range": None,
                "content_type": "video/mp4",
                "status_code": 200
            }


class S3StorageProvider(StorageProvider):
    """
    AWS S3 storage implementation.
    """
    def __init__(self, bucket_name: str):
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise ImportError(
                "boto3 is required for S3 storage. Run 'pip install boto3' to install it."
            )
        region = os.getenv("AWS_REGION", "us-east-2")
        self.s3_client = boto3.client(
            "s3",
            region_name=region,
            config=Config(signature_version="s3v4")
        )
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
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.s3_client.download_file(self.bucket_name, remote_name, local_path)
            return True
        except Exception as e:
            logger.error(f"S3 download_file error for {remote_name}: {e}", exc_info=True)
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

    # --- S3 Multipart Upload Implementation ---
    def initiate_multipart_upload(self, remote_name: str, content_type: str = "video/mp4") -> str:
        response = self.s3_client.create_multipart_upload(
            Bucket=self.bucket_name,
            Key=remote_name,
            ContentType=content_type
        )
        return response["UploadId"]

    def generate_presigned_upload_part_url(self, remote_name: str, upload_id: str, part_number: int) -> str:
        url = self.s3_client.generate_presigned_url(
            ClientMethod="upload_part",
            Params={
                "Bucket": self.bucket_name,
                "Key": remote_name,
                "UploadId": upload_id,
                "PartNumber": part_number
            }
        )
        return url

    def complete_multipart_upload(self, remote_name: str, upload_id: str, parts: List[Dict]) -> bool:
        sorted_parts = sorted(parts, key=lambda x: x["PartNumber"])
        self.s3_client.complete_multipart_upload(
            Bucket=self.bucket_name,
            Key=remote_name,
            UploadId=upload_id,
            MultipartUpload={"Parts": sorted_parts}
        )
        return True


    def abort_multipart_upload(self, remote_name: str, upload_id: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.s3_client.abort_multipart_upload(
                Bucket=self.bucket_name,
                Key=remote_name,
                UploadId=upload_id
            )
            return True
        except ClientError:
            return False

    def save_upload_part(self, upload_id: str, part_number: int, file_obj) -> bool:
        # S3 parts go directly from browser to AWS S3, bypassing this server
        raise NotImplementedError("save_upload_part is only for LocalStorageProvider")

    def list_parts(self, remote_name: str, upload_id: str) -> List[Dict]:
        parts = []
        kwargs = {
            "Bucket": self.bucket_name,
            "Key": remote_name,
            "UploadId": upload_id
        }
        while True:
            response = self.s3_client.list_parts(**kwargs)
            if "Parts" in response:
                for part in response["Parts"]:
                    parts.append({
                        "PartNumber": part["PartNumber"],
                        "ETag": part["ETag"]
                    })
            if response.get("IsTruncated"):
                kwargs["PartNumberMarker"] = response["NextPartNumberMarker"]
            else:
                break
        return parts

    def get_object_stream(self, remote_name: str, range_header: Optional[str] = None) -> Optional[Dict]:
        """
        Fetches an object stream directly from S3 using boto3 without saving to disk.
        Supports byte-range requests.
        """
        from botocore.exceptions import ClientError
        params = {"Bucket": self.bucket_name, "Key": remote_name}
        if range_header:
            params["Range"] = range_header
        try:
            response = self.s3_client.get_object(**params)
            return {
                "body": response["Body"],
                "content_length": response.get("ContentLength"),
                "content_range": response.get("ContentRange"),
                "content_type": response.get("ContentType", "video/mp4"),
                "status_code": 206 if range_header else 200
            }
        except ClientError:
            return None


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
