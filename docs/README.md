# Table Tennis Video Editor — Codebase Documentation

Welcome to the documentation for the **Table Tennis Video Editor** codebase! This directory contains technical architecture specifications, deployment guides, and feature design plans for maintainers and engineers.

---

## 📂 Documentation Directory Map

```text
docs/
├── README.md           # Master Entry Point, System Overview, & Feature Status
├── architecture/       # Active System Topology, Component Flows, & Database Specifications
├── deployment/         # Production Deployment, Operations, & GitHub Actions Setup Guides
└── plans/              # Feature Design Proposals (Divided into future/ and completed/)
```

### Subfolder Overview

* 🏗️ **[`architecture/`](./architecture/)**: Single source of truth for current system design, network topology, component interaction flows, and database schemas (DynamoDB / SQLite).
* ☁️ **[`deployment/`](./deployment/)**: Operational playbooks for deploying to AWS EC2, configuring S3 buckets, setting environment variables, and configuring GitHub Actions CI/CD.
* 📋 **[`plans/`](./plans/)**: Detailed feature implementation plans and RFCs:
  * **`plans/future/`**: Technical specs for upcoming/proposed features not yet built (e.g. AWS Batch GPU rendering).
  * **`plans/completed/`**: Historical implementation records for features already shipped to production.

---

## ⚡ System Architecture Overview

The **Table Tennis Video Editor** is a full-stack web application for table tennis players and coaches to automate match scoring, rally highlight clipping, and HD scoreboard overlay rendering.

* **Frontend**: React 18, TypeScript, Vite, Vanilla CSS.
* **Backend API**: Python 3.11, FastAPI, Uvicorn, Pydantic v2.
* **Core Engine**: OpenCV, Pillow (PIL), FFmpeg (`libx264` / `h264_videotoolbox` / `h264_nvenc`).
* **Database & Storage**: Amazon DynamoDB (NoSQL) & Amazon S3 (Video Objects).
* **Security & Multi-Tenancy**: Google OAuth 2.0 + Beta Email Whitelist + Strict `user_id` record isolation.

For detailed diagrams and component flows, read **[architecture/ARCHITECTURE.md](./architecture/ARCHITECTURE.md)**.

---

## ✅ 1. Implemented Features (Live in Production)

### 🎥 Match Upload & Video Player
* **Direct S3 Multipart Chunked Uploads**: 8MB chunked uploading directly from browser to S3 with upload progress indicators.
* **Direct S3 Progressive Streaming**: 307 pre-signed S3 redirects with explicit `video/mp4` MIME headers for progressive browser playback and GPU decoding.
* **Video Keyboard Seek Controls**: Dedicated hotkeys (`Space` for play/pause, `◄`/`►` and `,`/`.` for `±2.0s` seek, `Shift + ◄/►` for fine `±0.1s` seek, `▲`/`▼` for `±1m` jump).

### 🏓 Point Logging, Scoreboard & Event Editing
* **Interactive Point Logging**: One-click (`1`/`A` or `2`/`S`) point logging with automatic score incrementation and game transitions.
* **Inline Event Details Editor**: Edit start/end timestamps and change point winners directly in the point log list with 1-click current playback time capture buttons (`Start` / `End`).
* **Dynamic Score Derivation**: Score sequence and game numbers are derived dynamically on load and edit (`compute_scores_and_games`), keeping DB & UI scores consistent.
* **Game 1 First Server Selection**: Interactive server toggle (`Jonsen` vs `Eugene`) updating ITTF 2-point serve rotation dynamically.
* **Interactive Highlight Star Toggle**: 1-click hoverable star button on point logs to mark rally highlights.
* **Player Timeout Logging**: Log ITTF 60-second timeouts taken by specific players per point log.

### 📊 Match Analytics & Reporting
* **Zero-Input Table Tennis Match Analytics**: Serve/Return Win %, Tactical Rally Duration Buckets (`<4s`, `4-8s`, `>8s`), Max Point Streaks, and 1-click jump to longest rally.
* **CSV Event Export**: Export full match point logs and metadata to structured CSV files.

### ⚙️ Video Rendering & Overlay Engine
* **HD Scoreboard Overlay Rendering**: Custom Pillow (PIL) + FFmpeg 1080p score overlay generator with bundled TTF fonts.
* **Platform-Aware Hardware Encoding**: Automatically selects `h264_videotoolbox` on macOS and `libx264` on Linux EC2 servers.
* **Render History & Live Polling**: Asynchronous background rendering with 2.5s live status polling, execution time pills (e.g. `⚡ 14.2s`), and instant preview playback.

### 🔐 Security & Multi-Tenancy
* **Google OAuth 2.0 & Beta Whitelist**: Authenticated login with `ALLOWED_BETA_EMAILS` environment variable checks (supporting GitHub Actions Variables & Secrets).
* **Strict Multi-Tenant Match Isolation**: User sub IDs isolated on all DB records and S3 keys (`uploads/{user_id}/{match_id}.mp4`).
* **Match Metadata Renaming & Event Propagation**: Edit match titles & player names, with automated propagation to all event winner fields.

---

## 🚀 2. Future Planned Features

### ⚡ Hardware-Accelerated Cloud Video Rendering
* **AWS Batch On-Demand GPU Rendering** (`Spec Ready`)
  * Offload heavy FFmpeg rendering jobs to `g4dn.xlarge` (NVIDIA T4 GPU) instances running `h264_nvenc`.
  * **Goal**: Sub-minute video rendering with **$0.00 idle cost** (Scale-to-Zero).
  * *Detailed Architecture Plan*: [docs/plans/future/AWS_BATCH_GPU_RENDERING.md](./plans/future/AWS_BATCH_GPU_RENDERING.md)

### 🧹 Infrastructure & Storage Resilience
* **Orphaned S3 Multipart Upload Cleanup** (`Planned`)
  * Configure S3 Lifecycle Rules (`AbortIncompleteMultipartUpload`) to automatically delete incomplete 50MB upload chunks after 7 days to prevent storage bloat.
* **Explicit Upload Failure State Indicator** (`Planned`)
  * Update UI upload status from staying stuck at "Uploading" to explicitly displaying "Upload Failed" with a retry button upon network interruption.

### 🎨 UI Onboarding & Scoreboard Enhancements
* **First-Time User UI Onboarding & Guide**: Add an inline interactive guide explaining how to log full matches, edit events, and render highlights.
* **Active Server Indicator Carat on Scoreboard**: Add a visual serve indicator (e.g. `🏓`) next to the active server's name on the live video overlay.
