# Table Tennis Highlights Automator

A professional Python tool for automating table tennis highlight creation.

## 📁 Project Structure
Following the standard `src/` layout for maintainability:
- `src/tt_video_editor/`: Core package logic.
- `tests/`: Unit and integration tests.
- `scripts/`: Internal script entry points.
- `perf_scripts/`: Performance profiling tools.
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
python tt_automator.py <input> <output> --names "Player1,Player2"
```

### 3. Usage Modes
- **Manual Mode (Default)**: Mark points with key presses.
  ```bash
  python tt_automator.py input.mp4 output.mp4 --mode manual --explicit-start
  ```
- **Hybrid Mode**: Audio-based rally detection with review.
  ```bash
  python tt_automator.py input.mp4 output.mp4 --mode hybrid
  ```
- **Event Persistence**: Load previous logs to re-render instantly.
  ```bash
  python tt_automator.py input.mp4 output.mp4 --load-events events.json
  ```

## ⌨️ Controls (Manual Mode)
- `SPACE`: Pause/Play
- `D`: Mark **START** of point (requires `--explicit-start`)
- `A` / `S`: Point for **P1** / **P2** (ends clip)
- `Shift+A` / `Shift+S`: Record **Timeout**
- `Z`: **Undo** last action
- `Left/Right` or `,/.`: Seek +/- 1 second
- `Q`: Quit & Save Events

## 🧪 Testing & Profiling
```bash
# Run Unit Tests
python -m unittest discover tests

# Run Profiling
python perf_scripts/profile_startup.py tests/testgame1.MOV
```

## 🛠️ Configuration
Linting and project settings are managed in `pyproject.toml`.
