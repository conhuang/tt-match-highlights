# Database Setup & Configuration

This project implements an abstracted database repository pattern. You can toggle between a local **SQLite** database for development and **Amazon DynamoDB** for AWS production.

---

## 1. Local Development (SQLite)
By default, the application runs on **SQLite**. It requires zero configuration, zero servers, and zero Docker containers to run.

* **Configuration**: By default, `DB_TYPE` is set to `sqlite`. It automatically creates a single database file named `metadata.db` in the project root.
* **To override path**:
  ```bash
  export DB_TYPE="sqlite"
  export SQLITE_DB_PATH="custom_path.db"
  ```

---

## 2. Production (AWS DynamoDB)
In the production Fargate tasks, the application connects to **Amazon DynamoDB**.

* **Requirements**:
  1. A DynamoDB table named `tt_video_editor_matches` with partition key `id` (String).
  2. The ECS Task Role must have the `ECS-DynamoDB-MatchesPolicy` attached.

* **Environment Variables to set**:
  ```bash
  export DB_TYPE="dynamodb"
  export DYNAMODB_TABLE_NAME="tt_video_editor_matches"
  export AWS_REGION="us-east-2"
  ```

---

## 3. Data Model & File Naming Design Notes

### 📋 Match Data Schema (Pydantic)
Your data model is defined in [app/models.py](file:///Users/conniehuang/code/tt/tt_video_editor/app/models.py). The core schemas are structured to ensure compatibility between SQLite, DynamoDB, and the Python video renderer:

* **`Match`**: The root document representing a match.
  - `id`: `ShortUUID` (generated automatically, e.g., `"vytxeJKJygguct7vC6Lxw"`).
  - `owner_username`: Defaulting to `"admin"`, prepared for multi-tenancy in Phase 5.
  - `name`: Human-readable match name.
  - `player1` / `player2`: The names of the players.
  - `video_filename`: The unique storage name of the video.
  - `original_filename`: The original human-readable uploaded file name (for display in UI).
  - `events`: List of points/events.
* **`Event`**: Individual points/timeouts inside a match.
  - `start` / `end`: Timestamps in seconds.
  - `winner` / `timeout_player`: Associated player names.
  - `isHighlight`: Toggle flag for compile inclusion.
  - `game`: The game number.
  - `score_before`: Score before the point played.

### 🎥 S3 File Naming & Uniqueness Conventions
To prevent file name collisions (e.g., if two users upload files named `match.mp4`), we isolate the storage naming from the human-readable naming:

1. **Deterministic S3 Keys**:
   When a video is uploaded, it is automatically renamed to match its unique `Match ID` before saving to S3:
   - **Raw Upload path**: `uploads/{match_id}.mp4`
   - **Rendered Highlights path**: `renders/{match_id}_highlights.mp4`
   *Example*: `uploads/vytxeJKJygguct7vC6Lxw.mp4`

2. **Displaying the Original Name**:
   - The unique filename (`vytxeJKJygguct7vC6Lxw.mp4`) is saved in `Match.video_filename`.
   - The user's original uploaded filename (e.g., `final_ping_pong_game.mp4`) is saved in `Match.original_filename` to show inside their dashboard.