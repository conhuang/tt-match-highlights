# React Migration Plan - Table Tennis Highlights Automator

We are migrating the existing static frontend (`app/static/index.html` and `app/static/app.ts`) to a modern React SPA powered by **Vite**, **TypeScript**, and **Lucide Icons**, with a premium dark-mode **Vanilla CSS** design system.

## 📁 Architecture & Build Pipeline

1. **Frontend Location**: React source lives in `frontend/`.
2. **Vite Build Target**: `vite.config.ts` outputs production assets directly to `../app/static` with `base: "/static/"`.
3. **FastAPI Integration**: FastAPI serves the React app via `app.mount("/static", StaticFiles(directory="app/static"), name="static")`. Accessing `/static/index.html` will render the React app seamlessly.

## 📊 Data Models & State Structure

- **`Event`**:
  - `start: number` (seconds with decimal precision)
  - `end: number` (seconds with decimal precision)
  - `winner: string` (Player 1 or Player 2 name)
  - `timeout_player?: string | null`
  - `isHighlight: boolean`
  - `game: number` (Active game, default 1)
  - `score_before: string` (Backend computed, e.g. "0-0")
- **`Match`**:
  - `id: string`
  - `name: string`, `player1: string`, `player2: string`
  - `created_at: string`
  - `video_filename?: string | null`, `original_filename?: string | null`
  - `rendered_video_filename?: string | null`, `video_url?: string | null`, `rendered_video_url?: string | null`
  - `events: Event[]`

## ⚡ React Component Hierarchy

```
App.tsx
 ├── DashboardView
 │    ├── MatchForm (Match Name, Player 1, Player 2 inputs)
 │    ├── UploadZone (Drag & Drop, 50MB parallel chunked S3/Local multipart uploader)
 │    └── MatchesList (Match cards, Status badges, Delete confirmation modal/button)
 └── WorkspaceView
      ├── WorkspaceHeader (Back button to Dashboard, Match title & players display)
      ├── VideoSection (Controlled HTML5 Video element with custom ref for precise timestamp seeking)
      ├── StatusPanel (Pending start time display, active status indicator)
      ├── ShortcutSheet (Interactive key binding cheat sheet)
      └── SidebarLogs
           ├── GameSelector (Game 1-9 selector)
           ├── EventCardList (Chronological event cards, time-link buttons, winner tags, highlight ⭐ toggle, timeout selector, delete button)
           └── WorkspaceActions (Manual Save & Render Highlights triggers)
```

## ⌨️ Keyboard Shortcuts Hook (`useKeyboardShortcuts`)

- Global `keydown` event listener attached when `WorkspaceView` is mounted.
- Form Element Guard: Bypasses execution when focus is inside `<input>`, `<textarea>`, or `<select>`.
- Controls:
  - `SPACE`: Toggle play/pause on video player (`e.preventDefault()`).
  - `E` / `D`: Set `pendingStartTime = videoPlayer.currentTime`.
  - `1` / `A`: Log point won by **Player 1** (requires `pendingStartTime < currentTime`).
  - `2` / `S`: Log point won by **Player 2** (requires `pendingStartTime < currentTime`).
  - `Z`: Undo last point log (`events.pop()`).
- Automatically triggers auto-save (`PUT /api/matches/{id}`) on point addition, deletion, or modification.

## 🚀 Multipart Upload Engine (`uploadVideoMultipart`)

- **Chunk Size**: 50MB (`50 * 1024 * 1024` bytes).
- **Concurrency Limit**: 3 parallel chunk uploads.
- **Workflow**:
  1. `POST /api/matches/{match_id}/upload/initialize` -> Returns `upload_id` and pre-signed part URLs.
  2. Queue chunk uploads via `XMLHttpRequest` / `fetch` to capture progress events (`xhr.upload.onprogress`).
  3. Aggregate progress across parts to render smooth progress bar & percentage.
  4. On failure, invoke `POST /api/matches/{match_id}/upload/abort`.
  5. On all chunks complete, call `POST /api/matches/{match_id}/upload/complete` with array of `{ PartNumber, ETag }`.

## 🎨 Design System Specifications

- **Theme**: Premium Glassmorphic Dark Mode.
- **Colors**:
  - Background: `#070708` to `#121214` linear gradient.
  - Cards: `#121216` with `1px solid rgba(255, 255, 255, 0.08)`.
  - Player 1 Accent: `#3b82f6` (Neon Blue).
  - Player 2 Accent: `#f87171` (Neon Coral Red).
  - Success / Start Time: `#10b981` (Emerald Green).
- **Animations**: Sub-200ms cubic-bezier transitions on hover, focus, dragover, and state changes.

## 📋 Migration Execution Steps

1. Run `npx create-vite@5 frontend --template react-ts`.
2. Configure `vite.config.ts` (`outDir: "../app/static"`, `base: "/static/"`).
3. Install dependencies (`lucide-react`).
4. Build `frontend/src/` components, styles, and hooks.
5. Compile React app (`npm run build` inside `frontend/`).
6. Test end-to-end integration with FastAPI backend.
