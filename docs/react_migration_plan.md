# React Migration Plan - Table Tennis Highlights Automator

We are migrating the existing HTML/TS frontend (`app/static/index.html` and `app/static/app.ts`) to a modern React frontend powered by **Vite** and **TypeScript** with an enhanced, premium **Vanilla CSS** design system.

## 🛠️ Architecture & Setup

1. **Subdirectory Setup**: We will create a `frontend/` directory in the project root to keep the frontend source separate from the Python backend code.
2. **Vite Project**: We will initialize a Vite project with React + TypeScript template.
3. **Build Target**: We will configure `vite.config.ts` to output files directly into the backend's static directory (`app/static/`), setting the base URL to `/static/` so that the FastAPI server can serve the React SPA directly.
4. **Clean-up**: We will move/remove the old static assets once the React app is ready.

## ⚡ React App Components

We will build the frontend around a modular structure:
- **`App.tsx`**: Manages view state (Dashboard vs. Workspace) and selected match.
- **`Dashboard/`**:
  - **`MatchForm.tsx`**: Standardized name and player input form.
  - **`UploadZone.tsx`**: Premium drag-and-drop region featuring concurrent, chunked multipart uploads (parallel chunk queueing, concurrency limit of 3, progress bar, upload abort).
  - **`MatchesList.tsx`**: Dynamic display of matches with status indicator, and delete buttons.
- **`Workspace/`**:
  - **`WorkspaceHeader.tsx`**: Breadcrumb nav back to Dashboard, displaying match names.
  - **`VideoSection.tsx`**: Styled video player that responds to seek actions and state.
  - **`ShortcutSheet.tsx`**: Interactive hotkey reference panel.
  - **`SidebarLogs.tsx`**: Game number selector, list of chronological points with time-link seek buttons, score indicators, toggles for highlights, dropdowns for timeouts, and delete actions.
  - **`KeyboardManager`**: Custom hooks/handlers for workspace keyboard shortcuts (`SPACE` to play/pause, `E/D` to mark clip start, `1/A` or `2/S` to record player points, `Z` to undo).

## 🎨 Premium CSS Styling System

We will implement a custom CSS system in `frontend/src/index.css` following our premium UI rules:
- **Neon Dark Mode**: Deep grey/black base (`#070708` to `#121214`), translucent glassmorphism borders (`rgba(255, 255, 255, 0.08)`), high-contrast white and light grey typography.
- **Accent Accents**: Vibrant neon blue (`#3b82f6` / `#60a5fa`) for Player 1 / generic primary highlights, neon coral-red (`#f87171` / `#ef4444`) for Player 2 / warnings, and neon green (`#10b981` / `#34d399`) for successful uploads/start times.
- **Micro-animations**: Smooth hover transitions (`transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1)`), scales on buttons, glowing borders on focus/dragover.

## 🚀 Step-by-Step Migration Plan

1. **Vite Setup**:
   - Initialize Vite template.
   - Install required packages (e.g. `lucide-react` for premium icons).
2. **Build Configuration**:
   - Modify `vite.config.ts` to output build to `../app/static` and set base path to `/static/`.
3. **Core API & Upload logic implementation**:
   - Implement the parallel multipart uploader function in React state or custom helper.
4. **Develop Dashboard and Workspace Components**:
   - Replicate and enhance design with responsive grids and high-quality CSS layouts.
5. **Add Hotkeys & Global Handlers**:
   - Implement standard `window` keydown listeners cleanly inside a React hook context.
6. **Verify and Deploy**:
   - Build project (`npm run build`).
   - Run server and verify UI in the browser.
