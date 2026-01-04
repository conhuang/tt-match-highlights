import numpy as np
import cv2
import subprocess
import os
from scipy.io import wavfile

# Ground Truth from Manual Run (Step 285)
GROUND_TRUTH = [
    (16.1, 21.1), (28.2, 35.3), (47.3, 51.2), (61.0, 66.6), 
    (74.6, 79.2), (89.1, 94.3), (111.3, 117.2), (126.4, 130.2)
]

def extract_audio(video_path):
    audio_path = "temp_calibration_audio.wav"
    if not os.path.exists(audio_path):
        print("Extracting audio...")
        cmd = [
            "ffmpeg", "-y", "-i", video_path, 
            "-ac", "1", "-ar", "16000", 
            audio_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return audio_path

def detect_rallies(audio_path, threshold_ratio):
    rate, data = wavfile.read(audio_path)
    data = np.abs(data)
    max_val = np.max(data)
    if max_val == 0: return []
    
    threshold = max_val * threshold_ratio
    
    hits = np.where(data > threshold)[0]
    hits_sec = hits / rate
    
    rallies = []
    if len(hits_sec) == 0: return []
    
    current_start = hits_sec[0]
    current_end = hits_sec[0]
    
    # Clustering logic (Same as tt_automator)
    for h in hits_sec[1:]:
        if h - current_end < 2.0:
            current_end = h
        else:
            if current_end - current_start > 0.5:
                rallies.append((current_start, current_end))
            current_start = h
            current_end = h
    if current_end - current_start > 0.5:
        rallies.append((current_start, current_end))
        
    return rallies

def evaluate(detected, truth):
    # Simple overlap check: A detected rally is "True Positive" if it overlaps with a ground truth rally
    # False Positive if it doesn't overlap any.
    # False Negative if a ground truth isn't overlapped by any.
    
    tp = 0
    fp = 0
    fn = 0
    
    # Check TPs and FPs
    for d_start, d_end in detected:
        is_match = False
        for t_start, t_end in truth:
            # Overlap check
            if max(d_start, t_start) < min(d_end, t_end):
                is_match = True
                break
        if is_match:
            tp += 1
        else:
            fp += 1
            
    # Check FNs (approximate)
    for t_start, t_end in truth:
        is_covered = False
        for d_start, d_end in detected:
            if max(d_start, t_start) < min(d_end, t_end):
                is_covered = True
                break
        if not is_covered:
            fn += 1
            
    return tp, fp, fn

def main():
    video_path = "/Users/conniehuang/Desktop/personal/tt_video_editor/testgame1.MOV"
    audio_path = extract_audio(video_path)
    
    print(f"Running calibration on {video_path}...")
    print(f"Ground Truth Events: {len(GROUND_TRUTH)}")
    print("-" * 60)
    print(f"{'Threshold':<10} | {'Found':<6} | {'TP':<4} | {'FP':<4} | {'FN':<4} | {'Precision':<10}")
    print("-" * 60)
    
    best_ratio = 0.15
    best_fp = 999
    
    # Sweep
    for ratio in np.arange(0.05, 0.60, 0.05):
        rallies = detect_rallies(audio_path, ratio)
        tp, fp, fn = evaluate(rallies, GROUND_TRUTH)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        print(f"{ratio:.2f}       | {len(rallies):<6} | {tp:<4} | {fp:<4} | {fn:<4} | {precision:.2f}")
        
        # Optimize for maximizing Recall (low FN) first, then Precision (low FP)
        # We want FN=0 (catch all rallies), then minimize FP
        if fn == 0 and fp < best_fp:
            best_fp = fp
            best_ratio = ratio
            
    print("-" * 60)
    print(f"Recommendation: Use threshold_ratio = {best_ratio:.2f} (FP={best_fp})")
    
    # Cleanup
    if os.path.exists(audio_path):
        os.remove(audio_path)

if __name__ == "__main__":
    main()
