import argparse
import sys
import os
import subprocess
import json
import shutil
from datetime import timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description="Table Tennis Highlights Automator")
    parser.add_argument("input_file", help="Path to input video file")
    parser.add_argument("output_file", help="Path to output video file")
    parser.add_argument("--mode", choices=["manual", "hybrid"], default="manual", help="Operation mode")
    parser.add_argument("--explicit-start", action="store_true", help="Require 'S' key to mark start of point in manual mode")
    parser.add_argument("--names", default="Player 1,Player 2", help="Comma-separated player names")
    return parser.parse_args()

def get_video_properties(input_file):
    """Use ffprobe to get FPS and duration quickly."""
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)
        
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate,duration,nb_frames",
            "-of", "json", input_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        stream = data['streams'][0]
        # FPS is usually "30000/1001" or "30/1"
        num, den = map(float, stream['r_frame_rate'].split('/'))
        fps = num / den if den != 0 else 0
        
        duration = float(stream.get('duration', 0))
        if duration == 0 and 'nb_frames' in stream:
            duration = int(stream['nb_frames']) / fps
            
        return fps, duration
    except Exception as e:
        logger.warning(f"ffprobe failed, falling back to cv2: {e}")
        import cv2
        cap = cv2.VideoCapture(input_file)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        cap.release()
        return fps, duration


def process_video(events, args):
    from PIL import Image, ImageDraw, ImageFont
    from scoreboard.scoreboard_generator import ScoreboardGenerator
    
    if not events:
         return

    print("Generating overlays and processing rules...")
    
    # Init Logic
    game_num = 1
    p1_score = 0
    p2_score = 0
    p1_sets = 0
    p2_sets = 0
    p1_timeout_taken = False
    p2_timeout_taken = False
    
    # Ensure temp dir exists
    temp_dir = "temp_overlays"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    p1_name, p2_name = args.names.split(',')
    gen = ScoreboardGenerator(p1_name, p2_name)
    
    processed_segments = [] # List of (type, data)
    
    # Always start with Game 1 Card
    game_card_path = os.path.join(temp_dir, "game_1.png")
    gen.create_game_card(1, game_card_path)
    processed_segments.append({"type": "card", "path": game_card_path, "duration": 2.0})
    
    for i, event in enumerate(events):
        # 1. State BEFORE the point (for display)
        overlay_path = os.path.join(temp_dir, f"score_{i}.png")
        gen.create_scoreboard_image(p1_score, p2_score, p1_sets, p2_sets, overlay_path, 
                                     p1_timeout=p1_timeout_taken, p2_timeout=p2_timeout_taken)
        
        processed_segments.append({
            "type": "clip",
            "start": event['start'],
            "end": event['end'],
            "overlay": overlay_path
        })
        
        # 2. Update State AFTER the point
        if event['winner'] == p1_name:
            p1_score += 1
        else:
            p2_score += 1
            
        # Check Game End
        # Rule: >= 11 points AND diff >= 2
        if (p1_score >= 11 or p2_score >= 11) and abs(p1_score - p2_score) >= 2:
            # Game Over
            if p1_score > p2_score:
                p1_sets += 1
            else:
                p2_sets += 1
                
            # Reset
            p1_score = 0
            p2_score = 0
            game_num += 1
            
            # Add Game Card for NEXT game (if any events left or match not over)
            # Simplified: Just always add it if match isn't over (Best of 5, first to 3)
            if p1_sets < 3 and p2_sets < 3 and i < len(events) - 1:
                card_path = os.path.join(temp_dir, f"game_{game_num}.png")
                gen.create_game_card(game_num, card_path)
                processed_segments.append({"type": "card", "path": card_path, "duration": 2.0})

        # 3. Timeout Check (at the end of the clip)
        if event.get('timeout_winner'):
            tw = event['timeout_winner']
            if tw == p1_name: p1_timeout_taken = True
            else: p2_timeout_taken = True
            # Note: No popup segment added per user request, 
            # only the "T" indicator on the scoreboard will appear from next clip.

    print(f"Generated {len(processed_segments)} segments. Rendering with FFmpeg...")
    
    # FFmpeg Filter Complex Construction
    # Implementation strategy: Because filter_complex can get HUGE and slow/crash with many inputs,
    # we will render each 'clip' segment to a temp file with the overlay bonded, 
    # then use the concat demuxer (file list) for the final build.
    # This is much more stable for 50+ points.
    
    concat_list_path = "concat_list.txt"
    with open(concat_list_path, "w") as f:
        for idx, seg in enumerate(processed_segments):
            seg_output = os.path.join(temp_dir, f"seg_{idx}.mp4")
            
            if seg['type'] == "card":
                # Generate video from image WITH SILENT AUDIO
                # ffmpeg -loop 1 -i img.png -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 -t 3 ...
                cmd = [
                    "ffmpeg", "-y", 
                    "-loop", "1", "-i", seg['path'],
                    "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                    "-t", str(seg['duration']),
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-r", "30",
                    "-c:a", "aac", "-shortest",
                    seg_output
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
            elif seg['type'] == "clip":
                # Cut and Overlay
                # ffmpeg -ss start -to end -i video -i overlay -filter_complex "overlay" ...
                duration = seg['end'] - seg['start']
                cmd = [
                    "ffmpeg", "-y", 
                    "-ss", str(seg['start']), "-to", str(seg['end']),
                    "-i", args.input_file,
                    "-i", seg['overlay'],
                    "-filter_complex", "[0:v][1:v]overlay=0:0[outv]",
                    "-map", "[outv]", "-map", "0:a", # Keep audio
                    "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-pix_fmt", "yuv420p", "-r", "30",
                    seg_output
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Add to concat list
            # Concat demuxer requires absolute paths or relative safe paths
            f.write(f"file '{os.path.abspath(seg_output)}'\n")
            print(f"Rendered segment {idx+1}/{len(processed_segments)}")

    # Final Concat
    print("Concatenating segments...")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-c", "copy", args.output_file
    ])
    
    print(f"Done! Saved to {args.output_file}")
    
    # Cleanup 
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    if os.path.exists(concat_list_path):
        os.remove(concat_list_path)

def main():
    args = parse_args()
    fps, duration = get_video_properties(args.input_file)
    print(f"Video detected: {duration:.2f}s @ {fps} fps")
    
    events = []
    if args.mode == "manual":
        from main.manual_mode import run_manual_mode
        events = run_manual_mode(args)
    elif args.mode == "hybrid":
        from main.hybrid_mode import run_hybrid_mode
        events = run_hybrid_mode(args)
        
    if events:
        process_video(events, args)
    else:
        print("No events recorded. Exiting.")

if __name__ == "__main__":
    main()
