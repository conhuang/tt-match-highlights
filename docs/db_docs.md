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

---

## 4. Troubleshooting & Deployment Best Practices

### 🚨 Issue: "Match List Disappears After Every Cloud Deployment"

#### Root Cause:
If `DB_TYPE` is omitted from your cloud deployment environment variables (AWS App Hosting / ECS Fargate / App Runner / Render / Railway), the app defaults to `DB_TYPE=sqlite`. SQLite writes match records to `metadata.db` on the container's local disk.

Cloud containers have **ephemeral (temporary) disks**. When a new deployment occurs:
1. The old container is terminated and destroyed.
2. A new container boots up with a blank filesystem.
3. The old `metadata.db` is gone, causing all saved matches to disappear.

#### Resolution Strategies:

1. **Separate DynamoDB Tables per Environment (Recommended)**:
   Create separate DynamoDB tables to isolate development from production:
   - **Production Table**: `tt_video_editor_matches_prod`
   - **Staging / Dev Table**: `tt_video_editor_matches_dev`

   **Production Deployment Settings**:
   ```env
   DB_TYPE=dynamodb
   DYNAMODB_TABLE_NAME=tt_video_editor_matches_prod
   AWS_REGION=us-east-2
   ```

   **Local Development (`.env.dev`)**:
   ```env
   DB_TYPE=dynamodb
   DYNAMODB_TABLE_NAME=tt_video_editor_matches_dev
   AWS_REGION=us-east-2
   ```

2. **DynamoDB Serialization & Pagination (Built-in Fixes)**:
   - **Float to Decimal**: AWS `boto3` DynamoDB SDK rejects Python `float` timestamps (e.g., `start: 61.01`). The repository layer automatically converts `float` to `Decimal` before calling `put_item`/`update_item`, and converts back to `float` for API responses.
   - **Pagination**: The scan method uses `LastEvaluatedKey` loops to handle large table datasets (>1MB).

3. **Cleaning Orphaned S3 Files**:
   - **Is it safe to delete S3 files without matching DB entries?** Yes. The application queries DynamoDB to list matches. S3 files without DB entries are orphaned and can be safely deleted.
   - **Incomplete Multipart Uploads**: Set an AWS S3 Lifecycle Rule to automatically delete incomplete multipart upload chunks after 1–7 days to avoid storage costs from interrupted uploads.