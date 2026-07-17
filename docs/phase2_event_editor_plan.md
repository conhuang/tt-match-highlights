# Phase 2: Keystroke Event Editor & REST Integration Plan

We are building the Match Event Editor. This document details the step-by-step layout design, keyboard listener mechanics, and an incremental **Test-Driven Backend-First Verification Plan**.

---

## 💻 1. Backend-First & Unit-Test-Driven Implementation

To ensure absolute reliability, we implement the backend API and validation layer first, locking it down with automated unit tests before building the frontend.

### 📋 Pydantic Model Updates & Warning Fixes
When updating matches via `PUT /api/matches/{match_id}`, we must ensure submodels (like the list of `Event` objects) preserve their Pydantic classes to avoid serializer warnings.
* **The fix**: Instead of setting fields using the dictionary dumped by `model_dump()`, we retrieve the validated objects directly from `match_update` using `getattr(match_update, field)`:
  ```python
  update_data = match_update.model_dump(exclude_unset=True)
  for field in update_data.keys():
      value = getattr(match_update, field)
      setattr(match, field, value)
  ```
  This preserves the Pydantic classes and keeps the server logs clean and warning-free.

### 🧪 API Test Suite (`tests/test_api.py`)
We have created a dedicated test client class to test all endpoints. It performs:
1. **Create Match (`POST /api/matches`)**: Verifies ID generation and default attributes.
2. **List & Get Matches (`GET /api/matches`, `GET /api/matches/{id}`)**: Verifies data retrieval.
3. **Update Match Events (`PUT /api/matches/{id}`)**: Adds multiple nested events (rallies, scores, highlights, timeouts) and verifies persistence in the database.
4. **Initialize Upload (`POST /api/matches/{id}/upload/initialize`)**: Verifies chunk calculations.
5. **Delete Match (`DELETE /api/matches/{id}`)**: Verifies metadata and storage clean-up.

---

## 🎨 2. Workspace Layout & UI Design

Once the backend passes all tests, we build the Single Page Application (SPA) UI:

### Left Column: Media & Keyboard Reference
* **Back Button**: Returns the user to the matches list dashboard.
* **HTML5 Video Player**: Plays the video using the dynamic `match.video_url`.
* **Keystroke Status Bar**: Displays the currently marked values (e.g., `Point Start: 14.2s` or `None`).
* **Shortcuts Cheatsheet**:
  * `SPACE`: Play / Pause (prevents page scrolling).
  * `E` or `D`: Set current frame as **Start Time** of the point.
  * `1` or `A`: Set **End Time** and log point for **Player 1**.
  * `2` or `S`: Set **End Time** and log point for **Player 2**.
  * `Z`: Undo last event log.

### Right Column: Events List (Sidebar)
A scrollable vertical list of all logged points. Each point card contains:
* **Timeline Range Button**: Clicking it seeks the video player directly to the point's start time (`video.currentTime = start_time`).
* **Winner Display**: Shows which player won the point.
* **Inline Editable Fields**:
  * Game Number (Defaults to `1`).
  * Score Before (Auto-increments, editable in case of errors).
  * Highlight Toggle (⭐ checkbox/icon).
  * Timeout Selector (None, Player 1, Player 2).
* **Trash Icon**: Removes the event from the local list.

---

## ⌨️ 3. Keyboard Event Engine

A global event listener on the `window`:
* **Disable when typing**: The listener is disabled if the user has focused any input field (e.g., editing the match name or editing a score), allowing standard typing.
* **Auto-Score Calculation**: When a point is won by Player 1 or Player 2, the client-side JavaScript will automatically increment the score for you (e.g., `0-0` -> `1-0`), reducing manual input.

