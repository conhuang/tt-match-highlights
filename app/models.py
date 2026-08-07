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
    game: Optional[int] = Field(None, description="Dynamically computed game number (1-indexed)")


class RenderOptions(BaseModel):
    highlights_only: bool = Field(False, description="Whether to include only tagged highlight rallies")
    include_scoreboard: bool = Field(True, description="Whether to overlay the dynamic live scoreboards")
    scoreboard_artwork: str = Field("classic", description="Scoreboard artwork design ('classic' or 'simple')")
    scoreboard_position: str = Field("bottom-left", description="Scoreboard quadrant position ('bottom-left', 'bottom-right', 'top-left', 'top-right')")
    scoreboard_theme: str = Field("dark-blue", description="Visual theme ('dark-blue', 'classic-black', 'vibrant-red', 'emerald-green', 'cyber-purple')")
    scoreboard_scale: float = Field(1.0, description="Scale multiplier (0.8 to 1.2)")
    scoreboard_sets_color: str = Field("gold", description="Color for set score ('gold', 'silver', 'cyan', 'green', 'red')")
    scoreboard_sets_bg: str = Field("transparent", description="Set column background style ('transparent', 'solid-dark', 'gold-badge', 'accent-blue', 'subtle-glass')")
    scoreboard_border_style: str = Field("rounded", description="Card corner style ('rounded' or 'sharp')")
    scoreboard_font_style: str = Field("modern", description="Typography style ('modern', 'condensed', 'serif', 'monospace')")
    include_game_cards: bool = Field(True, description="Whether to insert inter-game 'Game X' title cards")
    cpu_mode: bool = Field(True, description="Whether to use CPU software encoding (libx264) vs GPU hardware")


class RenderJob(BaseModel):
    id: str = Field(default_factory=lambda: shortuuid.uuid(), description="Unique identifier for this render job")
    type: str = Field("full_match", description="Type of render ('full_match' or 'highlights')")
    label: str = Field("Full Scored Match", description="Human-readable title for this render")
    filename: Optional[str] = Field(None, description="Filename of the rendered output video")
    options: RenderOptions = Field(default_factory=RenderOptions, description="Render configuration options")
    status: str = Field("rendering", description="Current status: 'rendering', 'completed', or 'failed'")
    progress: int = Field(0, description="Completion percentage (0 to 100)")
    stage: str = Field("Initializing", description="Human-readable stage description")
    error: Optional[str] = Field(None, description="Error message if rendering failed")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z", description="ISO timestamp of render start")
    completed_at: Optional[str] = Field(None, description="ISO timestamp of render completion")
    render_duration_seconds: Optional[float] = Field(None, description="Total render execution duration in seconds")
    video_duration_seconds: Optional[float] = Field(None, description="Actual duration of the output video in seconds")
    video_url: Optional[str] = Field(None, description="Playback/download URL for the rendered video")


class RenderCreate(BaseModel):
    type: Optional[str] = Field("full_match", description="Type of render ('full_match' or 'highlights')")
    label: Optional[str] = Field(None, description="Optional custom title for this render")
    options: Optional[RenderOptions] = Field(default_factory=RenderOptions, description="Render configuration options")


class MatchBase(BaseModel):
    name: str = Field(..., description="Descriptive name of the match (e.g. 'Jonsen vs. Ryan Lin')")
    player1: str = Field(..., description="Name of Player 1")
    player2: str = Field(..., description="Name of Player 2")
    first_server: Optional[str] = Field("player1", description="Player who served first in Game 1 ('player1' or 'player2')")


class MatchCreate(MatchBase):
    pass


class MatchUpdate(BaseModel):
    name: Optional[str] = None
    player1: Optional[str] = None
    player2: Optional[str] = None
    first_server: Optional[str] = None
    events: Optional[List[Event]] = None
    renders: Optional[List[RenderJob]] = None
    video_filename: Optional[str] = None
    original_filename: Optional[str] = None
    rendered_video_filename: Optional[str] = None
    fps: Optional[float] = None
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None


class Match(MatchBase):
    """
    Represents a full Match record stored in the database.
    """
    id: str = Field(default_factory=lambda: shortuuid.uuid(), description="Unique ShortUUID identifier for the match")
    owner_username: Optional[str] = Field("admin", description="The email address of the account that uploaded this match")
    owner_id: Optional[str] = Field(None, description="The permanent Google sub ID of the owner")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z", description="ISO timestamp of match creation")
    video_filename: Optional[str] = Field(None, description="Filename of the uploaded raw video")
    original_filename: Optional[str] = Field(None, description="Original human-readable filename uploaded by the user")
    rendered_video_filename: Optional[str] = Field(None, description="Filename of the compiled highlights video output")
    fps: Optional[float] = Field(None, description="Frames per second of the source video")
    duration: Optional[float] = Field(None, description="Duration in seconds of the source video")
    width: Optional[int] = Field(None, description="Width in pixels of the source video")
    height: Optional[int] = Field(None, description="Height in pixels of the source video")
    events: List[Event] = Field(default_factory=list, description="Ordered list of marked points/events")
    renders: List[RenderJob] = Field(default_factory=list, description="List of generated renders for this match")


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
                        "game": 1
                    },
                    {
                        "start": 25.0,
                        "end": 31.4,
                        "winner": "Ryan Lin",
                        "timeout_player": "Jonsen",
                        "isHighlight": False,
                        "game": 1
                    }
                ]
            }
        }
