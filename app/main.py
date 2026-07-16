import os
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.staticfiles import StaticFiles
from typing import List

from app.models import Match, MatchCreate, MatchUpdate
from app.database import get_db_repository
from app.storage import get_storage_provider

app = FastAPI(title="Table Tennis Highlights API")

# Initialize database repository and storage provider
db = get_db_repository()
storage = get_storage_provider()

# Mount static frontend files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Mount local storage folder if it exists (allows local video playback)
local_storage_dir = os.getenv("LOCAL_STORAGE_DIR", "storage")
if os.path.exists(local_storage_dir):
    app.mount("/static/videos", StaticFiles(directory=local_storage_dir), name="videos")

@app.get("/")
def read_root():
    return {"message": "Hello World from FastAPI Backend!"}

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
    
    # Generate temporary pre-signed S3 playback URLs (or local paths)
    video_url = None
    if match.video_filename:
        video_url = storage.get_download_url(f"uploads/{match.video_filename}")
        
    rendered_url = None
    if match.rendered_video_filename:
        rendered_url = storage.get_download_url(f"renders/{match.rendered_video_filename}")

    # Return the metadata combined with the transient playback links
    response_data = match.model_dump()
    response_data["video_url"] = video_url
    response_data["rendered_video_url"] = rendered_url
    return response_data

@app.put("/api/matches/{match_id}", response_model=Match)
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
    
    # Update matching fields
    for field, value in update_data.items():
        setattr(match, field, value)
            
    # Save back to database
    updated = db.create_match(match.model_dump())
    return Match.model_validate(updated)

@app.post("/api/matches/{match_id}/upload")
async def upload_video(match_id: str, file: UploadFile = File(...)):
    """Streams and uploads a raw video file, then updates match metadata."""
    record = db.get_match(match_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match with ID {match_id} not found."
        )
    
    match = Match.model_validate(record)
    
    # Extract and validate file extension
    orig_filename = file.filename or "video.mp4"
    ext = os.path.splitext(orig_filename)[1].lower() or ".mp4"
    if ext not in [".mp4", ".mov", ".mkv", ".avi"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported video format. Please upload MP4, MOV, MKV, or AVI."
        )
        
    unique_storage_name = f"{match_id}{ext}"
    remote_path = f"uploads/{unique_storage_name}"
    
    # Stream upload direct to storage (preventing server memory footprint bloat)
    success = storage.upload_fileobj(file.file, remote_path)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save video to storage."
        )
        
    # Update match records
    match.video_filename = unique_storage_name
    match.original_filename = orig_filename
    db.create_match(match.model_dump())
    
    return {
        "id": match_id,
        "video_filename": unique_storage_name,
        "original_filename": orig_filename,
        "status": "upload_successful"
    }

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
