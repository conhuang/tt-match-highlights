# Table Tennis Highlights Automator

A professional Python tool for automating table tennis highlight creation.

## 📁 Project Structure
Following the standard `src/` layout for maintainability:
- `src/tt_video_editor/`: Core package logic.
- `tests/`: Unit and integration tests.
- `scripts/`: Internal script entry points (including automator and profiling tools).
- `pyproject.toml`: Project metadata and tool configuration.

## 🚀 Quick Start

### 1. Installation
Requires Python 3.8+ and `ffmpeg`.
```bash
pip install -e .
# Or manual: pip install opencv-python pillow numpy scipy
```

### 2. Run the Automator
```bash
# Main Entry Point
python scripts/tt_automator.py <input> <output> --names "Player1,Player2"
```

### 3. Usage Modes
- **Logging & Rendering (Default)**: Play video and mark events with key presses to build game events and render output.
  ```bash
  python scripts/tt_automator.py input.mp4 output.mp4 --names "Player1,Player2"
  ```
- **Event Persistence**: Load previous events JSON to re-render overlays and video instantly.
  ```bash
  python scripts/tt_automator.py input.mp4 output.mp4 --load-events events.json
  ```
- **Resume Logging**: Resume editing events where you left off.
  ```bash
  python scripts/tt_automator.py input.mp4 output.mp4 --resume-events events.json
  ```
- **Highlights Rendering**: Render both the full match AND highlights reel (2 output videos).
  ```bash
  python scripts/tt_automator.py input.mp4 output.mp4 --include-highlights
  ```

### 4. Example Usage
```bash
python scripts/tt_automator.py --names "Li/Nie,Zhang/Ly" --load-events ../jonsentt/ca_nat_2026/XDF_events.json ../jonsentt/ca_nat_2026/XDF.MOV --include-highlights ../jonsentt/ca_nat_2026/XDF_edited.mp4
```

## ⌨️ Controls (Manual Mode)
- `SPACE`: Pause/Play
- `E`: Mark **START** of point
- `1` / `2`: Point for **Player 1** / **Player 2** (ends clip)
- `3`: Record clip (NO SCORE CHANGE, ends clip)
- `H`: Toggle **HIGHLIGHT** status for current clip or last recorded event
- `Shift+1` (`!`) / `Shift+2` (`@`): Record **Timeout** for Player 1 / Player 2
- `Z`: **Undo** last action (clears current start mark, or removes last event and rewinds)
- `Left/Right` or `,/.`: Seek +/- 2 seconds (keyframe-aligned)
- `[` / `]`: Seek +/- 1 minute (keyframe-aligned)
- `Q`: Quit & Save Events

## 🧪 Testing & Profiling
```bash
# Run Unit Tests
python -m unittest discover tests

# Run Profiling
python scripts/profile_speed.py
```

## 🛠️ Configuration
Linting and project settings are managed in `pyproject.toml`.
