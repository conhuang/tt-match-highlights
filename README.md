# Table Tennis Highlights Automator

A Python tool designed to automate the creation of table tennis highlight videos. It takes raw match footage and generates a polished highlight reel with scoreboards, game transitions, and cut-out dead time.

## Features

- **Two Operation Modes:**
  - **Manual Mode:** Watch the video and log points with key presses.
  - **Hybrid Mode:** (Experimental) Automatically detects rallies using audio analysis, then prompts for quick review.
- **Automatic Editing:**
  - Removes dead time between points.
  - Generates a dynamic scoreboard overlay (Score, Sets).
  - Inserts "Game X" transition cards.
  - Concatenates everything into a final MP4.
- **Customizable:** Change player names, scoring logic handles standard ITTF rules (11 points, win by 2, Best of 5).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/conhuang/tt-match-highlights.git
    cd tt-match-highlights
    ```

2.  **Install Dependencies:**
    This tool requires Python 3.8+ and `ffmpeg` installed on your system path.
    ```bash
    pip install opencv-python pillow numpy scipy
    ```
    *Note: Ensure `ffmpeg` is accessible in your terminal.*

## Usage

### Basic Command
```bash
python tt_automator.py input.mp4 output.mp4 --names "Player1,Player2"
```

### Manual Mode (Default)
Watch the video and manually mark the winner of each point.
```bash
python tt_automator.py input.mp4 output.mp4 --mode manual --explicit-start --names "Alice,Bob"
```
**Controls:**
- `SPACE`: Pause/Play
- `D`: Mark **START** of point (recommended with `--explicit-start`)
- `A`: Point for **Player 1** (ends clip)
- `S`: Point for **Player 2** (ends clip)
- `Z`: **Undo** last event
- `Left/Right` or `,/.`: Seek +/- 1 second
- `Q`: Quit

### Hybrid Mode
Analyzes audio peaks (ball hits) to suggest potential rallies.
```bash
python tt_automator.py input.mp4 output.mp4 --mode hybrid --names "Alice,Bob"
```
The tool will present candidate clips for review.
**Review Controls:**
- `A`: Player 1 Won (Keep clip)
- `S`: Player 2 Won (Keep clip)
- `X`: Reject/Skip clip
- `SPACE`: Replay clip
- `Q`: Quit

## Calibration (Advanced)
If Hybrid Mode misses rallies, run the calibration script with ground truth timestamps to find the best audio threshold.
```bash
python calibrate.py
```
*(Requires editing `calibrate.py` with your specific video path and timestamps)*
