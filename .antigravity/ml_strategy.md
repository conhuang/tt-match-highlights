# Machine Learning Strategy for Table Tennis Automation

To improve the "Hybrid Mode" accuracy beyond simple volume thresholding, we can leverage Machine Learning. There are two main paths: **Audio Classification** (smarter listening) and **Computer Vision** (watching the game).

## Option 1: Audio Classification (Recommended First Step)
Instead of just checking *how loud* a sound is, we use a model to identify *what* the sound is (e.g., "Ball Hit" vs. "Shoe Squeak" vs. "Applause").

*   **Technology:** **YAMNet** (by Google) or a custom CNN trained on spectrograms.
*   **How it works:**
    1.  Convert small audio chunks (e.g., 0.5s) into spectrogram images.
    2.  Feed them into a pre-trained model fine-tuned on Table Tennis sounds.
*   **Hardware Requirements:**
    *   **Training:** Very light. Can train on a standard CPU (Mac) in minutes/hours.
    *   **Inference:** Extremely fast. Runs easily on any CPU.
*   **Pros:** Keeps the tool fast and lightweight.
*   **Cons:** Still struggles if the video has background music or loud commentary.

## Option 2: Computer Vision - Ball Tracking (TrackNet)
This is the "Gold Standard" for sports analytics. We track the x,y coordinates of the ball in every frame.

*   **Technology:** **TrackNet** (a specialized deep learning model for small high-speed objects).
*   **How it works:**
    1.  The model looks at 3 consecutive frames.
    2.  It outputs a "heatmap" of where the ball is.
    3.  We analyze the trajectory to detect "bounces" and "net hits".
*   **Hardware Requirements:**
    *   **Training:** Heavy. Requires separate NVIDIA GPU (Cloud or Desktop).
    *   **Inference:**
        *   **Standard CPU:** Slow (might take 2-3x video duration to process).
        *   **Mac (M1/M2/M3):** Good. Using the `MPS` (Metal Performance Shaders) acceleration in PyTorch, you can get near real-time performance.
*   **Pros:** Extremely accurate. Can count bounces to enforce rules (e.g., "point ends after 2 bounces").
*   **Cons:** Heavy dependency (PyTorch/TensorFlow), larger download size, slower processing.

## Option 3: Computer Vision - Action Recognition
Instead of tracking the tiny ball, we look at the players. Are they in a "ready stance"? Are they swinging? Or are they walking picking up the ball?

*   **Technology:** **YOLO** (Person Detection) or **Pose Estimation** (MoveNet/MediaPipe).
*   **How it works:**
    *   If players are walking towards the net -> Dead Time.
    *   If players are facing each other at table ends -> Rally Active.
*   **Hardware Requirements:**
    *   **Inference:** Modern lightweight models (YOLOv8, MediaPipe) run very fast on CPU/Mac Neural Engine.
*   **Pros:** Very robust for cutting out "dead time" (walking, towel breaks).
*   **Cons:** Doesn't give precise "point start/end" timing, just "activity" windows.

## Recommendation

**Hardware Check (Your Mac):**
Since you are on a Mac, you have access to **CoreML** and **MPS** (Metal Performance Shaders).
*   **Audio models** will fly (negligible load).
*   **Vision models** will work well if we use optimized versions (e.g., CoreML export of YOLO).

**Suggested Roadmap:**
1.  **Phase 1 (Low Hanging Fruit):** Implement **YAMNet** (Audio) to filter out "shoe squeaks" which are the main source of False Positives in your current Hybrid mode.
2.  **Phase 2 (Robustness):** Implement a simple **Motion/Activity Detector** (Vision). If the pixel difference between frames is low (static camera, no players moving), ignore the audio trigger.
3.  **Phase 3 (Professional):** Train/Deploy **TrackNet**.

I suggest we start with **Phase 1 (Audio Classification)** or **Phase 2 (Motion Filtering)** as they don't require heavy GPU setups.
