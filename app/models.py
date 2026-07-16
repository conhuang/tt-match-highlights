from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import shortuuid

class Event(BaseModel):
    """
    Represents a single rally/point or timeout event in a match.
    Matches the schema expected by the core rendering engine.
    """
    start: float = Field(..., description="Start time of the rally/point in seconds from video start")
    end: float = Field(..., description="End time of the rally/point in seconds from video start")
    winner: Optional[str] = Field(None, description="Name of the winning player for this point, or None if no score change")
    timeout_player: Optional[str] = Field(None, description="Name of the player who called a timeout after this point, or None")
    isHighlight: bool = Field(False, description="Whether this clip should be included in the highlights compilation")
    game: int = Field(1, description="The game number (1-indexed) this point belongs to")
    score_before: str = Field("0-0", description="The match score before this point played (e.g. '3-5')")


class MatchBase(BaseModel):
    name: str = Field(..., description="Descriptive name of the match (e.g. 'Jonsen vs. Ryan Lin')")
    player1: str = Field(..., description="Name of Player 1")
    player2: str = Field(..., description="Name of Player 2")


class MatchCreate(MatchBase):
    pass


class MatchUpdate(BaseModel):
    name: Optional[str] = None
    player1: Optional[str] = None
    player2: Optional[str] = None
    events: Optional[List[Event]] = None
    video_filename: Optional[str] = None
    original_filename: Optional[str] = None
    rendered_video_filename: Optional[str] = None


class Match(MatchBase):
    """
    Represents a full Match record stored in the database.
    """
    id: str = Field(default_factory=lambda: shortuuid.uuid(), description="Unique ShortUUID identifier for the match")
    owner_username: Optional[str] = Field("admin", description="The username of the account that uploaded this match")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="ISO timestamp of match creation")
    video_filename: Optional[str] = Field(None, description="Filename of the uploaded raw video")
    original_filename: Optional[str] = Field(None, description="Original human-readable filename uploaded by the user")
    rendered_video_filename: Optional[str] = Field(None, description="Filename of the compiled highlights video output")
    events: List[Event] = Field(default_factory=list, description="Ordered list of marked points/events")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "vytxeJKJygguct7vC6Lxw",
                "name": "Jonsen vs. Ryan Lin",
                "player1": "Jonsen",
                "player2": "Ryan Lin",
                "created_at": "2026-07-14T19:48:31.123456",
                "video_filename": "vytxeJKJygguct7vC6Lxw.mp4",
                "rendered_video_filename": "vytxeJKJygguct7vC6Lxw_highlights.mp4",
                "events": [
                    {
                        "start": 12.5,
                        "end": 18.2,
                        "winner": "Jonsen",
                        "timeout_player": None,
                        "isHighlight": True,
                        "game": 1,
                        "score_before": "0-0"
                    },
                    {
                        "start": 25.0,
                        "end": 31.4,
                        "winner": "Ryan Lin",
                        "timeout_player": "Jonsen",
                        "isHighlight": False,
                        "game": 1,
                        "score_before": "1-0"
                    }
                ]
            }
        }
