import os
from io import BytesIO
from fastapi import FastAPI, UploadFile, File, HTTPException, status, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional

from app.models import Match, MatchCreate, MatchUpdate
from app.database import get_db_repository
from app.storage import get_storage_provider

app = FastAPI(title="Table Tennis Highlights API")

# Initialize database repository and storage provider
db = get_db_repository()
storage = get_storage_provider()

@app.on_event("startup")
def compile_typescript_locally():
    """Autogenerates app.js from app.ts on server startup if tsc is installed locally."""
    if os.getenv("STORAGE_TYPE", "local") == "local":
        import subprocess
        try:
            # Check if tsc command is available
            subprocess.run(["tsc", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            ts_path = os.path.join("app", "static", "app.ts")
            if os.path.exists(ts_path):
                print(f"TypeScript: Autogenerating app.js from {ts_path}...")
                subprocess.run([
                    "tsc", ts_path,
                    "--target", "es6",
                    "--module", "es2015",
                    "--removeComments",
                    "--skipLibCheck"
                ], check=True)
                print("TypeScript: Compilation completed successfully!")
        except Exception:
            pass

from fastapi.responses import FileResponse

# Mount static frontend files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Mount local storage folder if it exists (allows local video playback)
local_storage_dir = os.getenv("LOCAL_STORAGE_DIR", "storage")
if os.path.exists(local_storage_dir):
    app.mount("/static/videos", StaticFiles(directory=local_storage_dir), name="videos")

@app.get("/")
def read_root():
    index_file = os.path.join("app", "static", "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Hello World from FastAPI Backend!"}


@app.get("/api/version")
def get_version():
    """Returns application version information, deployed commit SHA, and deployment timestamp."""
    return {
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "commit": os.getenv("GIT_COMMIT_SHA", "development"),
        "environment": os.getenv("ENVIRONMENT", "production"),
        "timestamp": os.getenv("DEPLOYMENT_TIMESTAMP", "unknown")
    }



# --- Schemas for Multipart Upload ---
class MultipartInit(BaseModel):
    filename: str
    file_size: int

class MultipartPart(BaseModel):
    PartNumber: int
    ETag: str

class MultipartComplete(BaseModel):
    upload_id: str
    parts: List[MultipartPart]
    original_filename: str

# --- Matches API Endpoints ---

@app.post("/api/matches", response_model=Match, status_code=status.HTTP_201_CREATED)
def create_match(match_in: MatchCreate):
    """Creates a new match metadata record in the database."""
    match = Match(
        name=match_in.name,
        player1=match_in.player1,
        player2=match_in.player2
    )
    created = db.create_match(match.model_dump())
    return Match.model_validate(created)

@app.get("/api/matches", response_model=List[Match])
def list_matches():
    """Lists all match records from the database."""
    records = db.list_matches()
    return [Match.model_validate(r) for r in records]

def _enrich_match_urls(match: Match) -> dict:
    """Generates temporary pre-signed S3 playback URLs (or local paths) for a match."""
    video_url = None
    if match.video_filename:
        video_url = storage.get_download_url(f"uploads/{match.video_filename}")
        
    rendered_url = None
    if match.rendered_video_filename:
        rendered_url = storage.get_download_url(f"renders/{match.rendered_video_filename}")

    response_data = match.model_dump()
    response_data["video_url"] = video_url
    response_data["rendered_video_url"] = rendered_url
    return response_data

@app.get("/api/matches/{match_id}")
def get_match(match_id: str):
    """Retrieves a single match details along with temporary pre-signed playback URLs."""
    record = db.get_match(match_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match with ID {match_id} not found."
        )
    
    match = Match.model_validate(record)
    return _enrich_match_urls(match)

@app.put("/api/matches/{match_id}")
def update_match(match_id: str, match_update: MatchUpdate):
    """Updates match details or event logs in the database."""
    record = db.get_match(match_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match with ID {match_id} not found."
        )
    
    match = Match.model_validate(record)
    update_data = match_update.model_dump(exclude_unset=True)
    
    # Update matching fields directly from match_update object, preserving Pydantic classes (eliminates serialization warnings)
    for field in update_data.keys():
        value = getattr(match_update, field)
        setattr(match, field, value)
        
    # Recalculate scores and game numbers if events list was modified
    if "events" in update_data and match.events:
        from app.scoring import compute_scores_and_games
        match.events = compute_scores_and_games(match.events, match.player1, match.player2)
            
    # Save back to database
    updated = db.create_match(match.model_dump())
    updated_match = Match.model_validate(updated)
    return _enrich_match_urls(updated_match)


# --- S3 Direct Multipart Upload Endpoints ---

@app.post("/api/matches/{match_id}/upload/initialize")
def initialize_multipart(match_id: str, init_data: MultipartInit):
    """Initiates a multipart upload and generates pre-signed URLs for each chunk."""
    record = db.get_match(match_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match with ID {match_id} not found."
        )
        
    ext = os.path.splitext(init_data.filename)[1].lower() or ".mp4"
    if ext not in [".mp4", ".mov", ".mkv", ".avi"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported video format. Please upload MP4, MOV, MKV, or AVI."
        )
        
    unique_storage_name = f"{match_id}{ext}"
    remote_path = f"uploads/{unique_storage_name}"
    
    try:
        # 1. Start the upload session on S3 or local mock
        upload_id = storage.initiate_multipart_upload(remote_path)
        
        # 2. Determine chunk size (default: 50MB per chunk)
        chunk_size = 50 * 1024 * 1024
        file_size = init_data.file_size
        num_parts = (file_size + chunk_size - 1) // chunk_size
        if num_parts == 0:
            num_parts = 1
            
        # 3. Generate pre-signed part upload URLs
        parts = []
        for part_num in range(1, num_parts + 1):
            url = storage.generate_presigned_upload_part_url(
                remote_name=remote_path,
                upload_id=upload_id,
                part_number=part_num
            )
            parts.append({
                "PartNumber": part_num,
                "UploadUrl": url
            })
            
        return {
            "upload_id": upload_id,
            "parts": parts,
            "unique_filename": unique_storage_name,
            "original_filename": init_data.filename
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize upload: {str(e)}"
        )

from fastapi.responses import FileResponse, StreamingResponse
import logging

logger = logging.getLogger(__name__)

def process_post_upload_tasks(match_id: str, remote_path: str, local_file_path: str):
    """Background task to run FastStart optimization and extract video metadata asynchronously."""
    from app.storage import S3StorageProvider
    from app.video_utils import extract_video_metadata, optimize_video_for_faststart

    try:
        if isinstance(storage, S3StorageProvider) or os.getenv("STORAGE_TYPE") == "s3":
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            if storage.download_file(remote_path, local_file_path):
                if optimize_video_for_faststart(local_file_path):
                    storage.upload_file(local_file_path, remote_path)
        elif os.path.exists(local_file_path):
            optimize_video_for_faststart(local_file_path)

        if os.path.exists(local_file_path):
            meta = extract_video_metadata(local_file_path)
            record = db.get_match(match_id)
            if record:
                match = Match.model_validate(record)
                match.fps = meta.get("fps")
                match.duration = meta.get("duration")
                match.width = meta.get("width")
                match.height = meta.get("height")
                db.create_match(match.model_dump())
    except Exception as e:
        logger.error(f"Background post-processing failed for match {match_id}: {e}")

@app.post("/api/matches/{match_id}/upload/complete")
def complete_multipart(match_id: str, complete_data: MultipartComplete, background_tasks: BackgroundTasks):
    """Completes the multipart upload by assembling the chunks and queuing post-processing tasks."""
    record = db.get_match(match_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match with ID {match_id} not found."
        )
        
    match = Match.model_validate(record)
    
    orig_filename = complete_data.original_filename
    ext = os.path.splitext(orig_filename)[1].lower() or ".mp4"
    unique_storage_name = f"{match_id}{ext}"
    remote_path = f"uploads/{unique_storage_name}"
    
    # Convert Pydantic parts to raw dict list for boto3/local uploader
    parts_list = [p.model_dump() for p in complete_data.parts]
    
    try:
        success = storage.complete_multipart_upload(
            remote_name=remote_path,
            upload_id=complete_data.upload_id,
            parts=parts_list
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to finalize video upload. The storage provider returned success=False."
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finalize video upload: {str(e)}"
        )

    # Update match database metadata immediately
    match.video_filename = unique_storage_name
    match.original_filename = orig_filename
    db.create_match(match.model_dump())

    # Schedule FastStart optimization and metadata extraction in background
    local_base = getattr(storage, "base_dir", "storage")
    local_file_path = os.path.join(local_base, remote_path)
    background_tasks.add_task(process_post_upload_tasks, match_id, remote_path, local_file_path)

    return {
        "id": match_id,
        "video_filename": unique_storage_name,
        "original_filename": orig_filename,
        "status": "upload_successful"
    }

@app.get("/api/matches/{match_id}/upload/parts")
def list_parts(match_id: str, upload_id: str, original_filename: str):
    """Lists already uploaded parts for an active multipart upload session."""
    ext = os.path.splitext(original_filename)[1].lower() or ".mp4"
    unique_storage_name = f"{match_id}{ext}"
    remote_path = f"uploads/{unique_storage_name}"
    
    try:
        parts = storage.list_parts(remote_name=remote_path, upload_id=upload_id)
        return {"parts": parts}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query uploaded parts: {str(e)}"
        )
    
@app.get("/api/matches/{match_id}/stream")
def stream_match_video(match_id: str, request: Request):
    """Serves the uploaded video with S3 pre-signed redirects or byte-range streaming without full file downloads."""
    record = db.get_match(match_id)
    if not record or not record.get("video_filename"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match video not found.")

    remote_name = f"uploads/{record['video_filename']}"

    # 1. If using S3 and request has no Range header, redirect directly to S3 pre-signed URL for native S3 streaming
    from app.storage import S3StorageProvider
    if isinstance(storage, S3StorageProvider) or os.getenv("STORAGE_TYPE") == "s3":
        if not request.headers.get("range"):
            presigned_url = storage.get_download_url(remote_name)
            if presigned_url:
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url=presigned_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    # 2. Stream requested range directly from storage (S3 boto3 stream or Local iterator) without downloading file to disk
    range_header = request.headers.get("range")
    stream_data = storage.get_object_stream(remote_name, range_header=range_header)

    if not stream_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video file missing on server or storage bucket.")

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": stream_data.get("content_type", "video/mp4"),
    }
    if stream_data.get("content_length") is not None:
        headers["Content-Length"] = str(stream_data["content_length"])
    if stream_data.get("content_range"):
        headers["Content-Range"] = stream_data["content_range"]

    if "body" in stream_data:
        def s3_iter():
            body = stream_data["body"]
            for chunk in body.iter_chunks(chunk_size=512 * 1024):
                yield chunk
        return StreamingResponse(s3_iter(), status_code=stream_data["status_code"], headers=headers)
    elif "iter" in stream_data:
        return StreamingResponse(stream_data["iter"], status_code=stream_data["status_code"], headers=headers)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to stream video content.")

@app.get("/api/matches/{match_id}/thumbnail")
def get_match_thumbnail(match_id: str, time: float = 0.0):
    """Returns a JPEG frame snapshot at the requested timestamp in seconds."""
    record = db.get_match(match_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Match with ID {match_id} not found.")
        
    match = Match.model_validate(record)
    if not match.video_filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Match does not have an uploaded video yet.")
        
    local_base = getattr(storage, "base_dir", "storage")
    local_path = os.path.join(local_base, "uploads", match.video_filename)
    if not os.path.exists(local_path):
        # If running in S3 mode (or file not present locally), fetch from storage provider
        success_download = storage.download_file(f"uploads/{match.video_filename}", local_path)
        if not success_download or not os.path.exists(local_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video file missing on server or storage bucket.")

        
    temp_thumb_dir = os.path.join(local_base, "temp_thumbs")
    thumb_path = os.path.join(temp_thumb_dir, f"{match_id}_{int(time * 100)}.jpg")
    
    if not os.path.exists(thumb_path):
        from app.video_utils import generate_frame_thumbnail
        success = generate_frame_thumbnail(local_path, thumb_path, timestamp=time)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate frame thumbnail."
            )
            
    return FileResponse(thumb_path, media_type="image/jpeg")


@app.post("/api/matches/{match_id}/upload/abort")
def abort_multipart(match_id: str, upload_id: str, original_filename: str):
    """Aborts a multipart upload and deletes all uploaded temporary chunks."""
    ext = os.path.splitext(original_filename)[1].lower() or ".mp4"
    unique_storage_name = f"{match_id}{ext}"
    remote_path = f"uploads/{unique_storage_name}"
    
    success = storage.abort_multipart_upload(
        remote_name=remote_path,
        upload_id=upload_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to abort multipart upload."
        )
    return {"status": "success", "message": "Multipart upload aborted."}

# --- Local Storage Part Upload Uploader (Mock API) ---
@app.put("/api/matches/upload/part")
async def upload_local_part(upload_id: str, part_number: int, request: Request):
    """Endpoint used ONLY by local storage provider to write temporary chunks."""
    body = await request.body()
    success = storage.save_upload_part(
        upload_id=upload_id,
        part_number=part_number,
        file_obj=BytesIO(body)
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to save part data."
        )
    return {"status": "success", "PartNumber": part_number, "ETag": f"local-etag-{part_number}"}

@app.delete("/api/matches/{match_id}")
def delete_match(match_id: str):
    """Deletes a match and cleans up its video files from storage."""
    record = db.get_match(match_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match with ID {match_id} not found."
        )
        
    match = Match.model_validate(record)
    
    # Delete associated files from storage
    if match.video_filename:
        storage.delete_file(f"uploads/{match.video_filename}")
    if match.rendered_video_filename:
        storage.delete_file(f"renders/{match.rendered_video_filename}")
        
    # Delete metadata record
    success = db.delete_match(match_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove match metadata."
        )
        
    return {"status": "success", "message": "Match and associated files deleted."}
