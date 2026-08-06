# Phase 3: Video Rendering & Multi-Render Management Plan

This document outlines the detailed architecture, backend APIs, background worker flow, database schemas, frontend UI components, and test-driven verification plan for **Phase 3: Video Rendering & Multi-Render Management**.

---

## 🎯 Objectives
1. Transform tagged match event JSON logs into fully scored, broadcast-ready table tennis videos with dynamic Pillow scoreboard overlays.
2. **Support Multiple Concurrent & Historical Renders** per match (e.g. Full Scored Match, Highlights Reel, or custom configurations without game cards).
3. **1080p Max Resolution Normalization**: Automatically cap 4K iPhone/camera source videos to 1080p (`1920x1080`) during rendering to boost processing speed by 4x.
4. **Vibrant Color Preservation & Tone Mapping**: Preserve standard SDR colors (BT.709) and automatically tone-map iPhone HDR/Dolby Vision videos so colors never look washed out.

---

## 🎬 1. Video Output Types: Full Match vs. Highlights Reel

The rendering engine generates distinct video experiences from the same event log based on user configuration:

### 🏆 **Full Match Video** (`highlights_only: false`)
- **Complete Story**: Concatenates **all** recorded rally clips sequentially from start time to end time.
- **Dynamic Live Scoreboard Overlay** (`include_scoreboard: true`): Displays a real-time broadcast overlay in the corner showing:
  - Running point score (e.g., `9 - 8`).
  - Current set score (e.g., `2 - 1`).
  - Player names & timeout badges.
  - Server indicator dot.
- **Inter-Game Title Cards** (`include_game_cards: true`): Automatically inserts a 2-second **"Game 1"**, **"Game 2"**, **"Game 3"** title card between games (triggered when a player reaches 11 points with a 2-point lead).

### ⭐ **Highlights Reel Video** (`highlights_only: true`)
- **Best Rallies Only**: Includes **only** the clips flagged with `isHighlight: true` (tagged by pressing `H` or toggling the star icon).
- **Fast-Paced Action**: Omits non-highlight points and inter-game title cards to produce a high-energy highlights reel.

---

## ⚙️ 2. Clean Positive Render Options Schema

All render options use positive boolean flags for clarity:

```json
{
  "highlights_only": false,       // false = Full Match, true = Highlights Reel
  "include_scoreboard": true,     // true = Overlay scoreboards, false = Clean video
  "include_game_cards": true,     // true = Insert "Game 1", "Game 2" cards, false = Direct clip transitions
  "cpu_mode": true                // true = x264 CPU software encoder, false = VideoToolbox GPU hardware
}
```

---

## 🏗️ 3. Multi-Render Architecture & Data Models

### Database Schema Updates (`Match.renders` Array)

Rather than storing a single `rendered_video_filename`, each match maintains a `renders` list tracking every render job with creation and completion timestamps:

```json
{
  "id": "match-uuid-123",
  "name": "Jonsen vs Ryan Lin",
  "player1": "Jonsen",
  "player2": "Ryan Lin",
  "renders": [
    {
      "id": "render-uuid-001",
      "type": "full_match",
      "label": "Full Scored Match",
      "filename": "match-uuid-123_render-uuid-001.mp4",
      "options": {
        "highlights_only": false,
        "include_scoreboard": true,
        "include_game_cards": true,
        "cpu_mode": true
      },
      "status": "completed",
      "progress": 100,
      "stage": "Complete",
      "error": null,
      "created_at": "2026-07-28T20:15:00Z",
      "completed_at": "2026-07-28T20:17:30Z",
      "video_url": "https://..."
    },
    {
      "id": "render-uuid-002",
      "type": "highlights",
      "label": "Highlights Reel",
      "filename": "match-uuid-123_render-uuid-002.mp4",
      "options": {
        "highlights_only": true,
        "include_scoreboard": true,
        "include_game_cards": false,
        "cpu_mode": true
      },
      "status": "rendering",
      "progress": 45,
      "stage": "FFmpeg Encoding (Segment 12/25)",
      "error": null,
      "created_at": "2026-07-28T20:18:00Z",
      "completed_at": null,
      "video_url": null
    }
  ]
}
```

---

## 🛠️ 4. Core Render Engine Adapter (`app/render_adapter.py`)

Create a dedicated adapter module connecting FastAPI background tasks to `tt_video_editor.core.process_video`:

```python
def run_render_task(
    match_id: str,
    render_id: str,
    render_type: str,
    render_options: dict,
    db_repo,
    storage_provider
):
    """
    Background worker function that:
    1. Fetches match events and raw video file.
    2. Downloads raw video to temp workspace if in S3 mode.
    3. Normalizes resolution (capping 4K inputs to 1080p max).
    4. Generates Pillow score overlay PNGs (if include_scoreboard=True).
    5. Runs FFmpeg concat/overlay filter graph with progress updates and HDR tone-mapping.
    6. Uploads output to S3 or moves to local storage (renders/match_id_render_id.mp4).
    7. Updates DB render job state to 'completed' (with completed_at timestamp) or 'failed'.
    8. Cleans up temporary segment files.
    """
```

---

## 📡 5. Backend API Endpoints (`app/main.py`)

### 1. Trigger New Render Job
`POST /api/matches/{match_id}/renders`
- **Request Body**:
  ```json
  {
    "type": "full_match",
    "label": "Full Scored Match",
    "options": {
      "highlights_only": false,
      "include_scoreboard": true,
      "include_game_cards": true,
      "cpu_mode": true
    }
  }
  ```
- **Behavior**:
  - Validates that match exists, has events logged, and has an uploaded original video.
  - Generates a unique `render_id` (UUID v4) and sets `created_at` timestamp.
  - Appends a new render job object with `status: "rendering"` to `match.renders`.
  - Queues `run_render_task` via FastAPI `BackgroundTasks`.
  - Returns HTTP 202 Accepted with the created `render_id` and initial job state.

### 2. List All Renders for a Match
`GET /api/matches/{match_id}/renders`
- Returns array of all render items, enriched with temporary pre-signed playback/download URLs (`video_url`).

### 3. Poll Specific Render Job Status
`GET /api/matches/{match_id}/renders/{render_id}/status`
- **Response Body**:
  ```json
  {
    "match_id": "match-uuid-123",
    "render_id": "render-uuid-002",
    "status": "rendering",
    "progress": 65,
    "stage": "FFmpeg Encoding",
    "error": null,
    "created_at": "2026-07-28T20:18:00Z",
    "completed_at": null,
    "video_url": null
  }
  ```

### 4. Delete Rendered Output
`DELETE /api/matches/{match_id}/renders/{render_id}`
- Removes the render entry from database `match.renders` array.
- Deletes the associated `.mp4` output file from S3 bucket or local storage (`renders/`).

---

## 🎨 6. Frontend UI Components (`frontend/src/`)

### 1. Render Modal & Positive Toggles
- Render options dialog allowing users to configure:
  - Mode: **Full Match** vs **Highlights Reel**.
  - Toggle: **Include Scoreboard** (`include_scoreboard`).
  - Toggle: **Include Game Cards** (`include_game_cards`).

### 2. Multi-Render History Drawer / Section
- Rendered Outputs panel in **Workspace** and **Dashboard Card**:
  - Displays all rendered videos for the match sorted by `created_at` timestamp.
  - **Live Progress Bar**: Shows percentage and stage text for any active render job.
  - **Preview & Play**: Click to preview the rendered MP4 in the workspace player.
  - **Download MP4**: Direct download button.
  - **Delete**: Trash icon to delete old or unwanted renders.

---

## 🧪 7. Verification & Test-Driven Plan

### Automated Unit Test Suite (`tests/test_render_integration.py`)
1. **Validation Tests**: Verify 400 Bad Request if rendering without events or raw video.
2. **Positive Signal Options Test**: Verify creating render jobs with `include_scoreboard` and `include_game_cards` options.
3. **Timestamps Test**: Verify `created_at` and `completed_at` ISO-8601 timestamps are recorded accurately.
4. **Multi-Render History Test**: Verify multiple render jobs exist independently in `match.renders`.
5. **Deletion Test**: Verify `DELETE /api/matches/{id}/renders/{render_id}` cleans up DB and storage.
6. **Mock Worker Execution Test**: Mock FFmpeg to verify full end-to-end status transition from `rendering` to `completed`.

---

## 🗓️ Implementation Steps

1. **Step 1 (Database & Schema)**: Update `Match` model and `SQLiteRepository` / `DynamoDBRepository` to support `renders: List[Dict]` list attribute with auto-migration.
2. **Step 2 (Render Adapter Engine)**: Build `app/render_adapter.py` with 1080p resolution capping, HDR tone-mapping, and positive options (`include_scoreboard`, `include_game_cards`).
3. **Step 3 (Multi-Render API Routes)**: Implement `POST /renders`, `GET /renders`, `GET /renders/{render_id}/status`, and `DELETE /renders/{render_id}` in `app/main.py`.
4. **Step 4 (Automated Tests)**: Write unit tests in `tests/test_render_integration.py` and verify 100% test pass rate.
5. **Step 5 (Frontend Multi-Render UI)**: Update React components (`WorkspaceHeader`, `MatchesList`, `SidebarLogs` / `RenderModal`) for positive options, live polling, timestamps, and video preview.
