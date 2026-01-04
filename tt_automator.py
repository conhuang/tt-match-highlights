#!/usr/bin/env python3
import argparse
import sys
import os
import cv2
import subprocess
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
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)
        
    cap = cv2.VideoCapture(input_file)
    if not cap.isOpened():
        logger.error(f"Could not open video file: {input_file}")
        sys.exit(1)
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0
    cap.release()
    return fps, duration

from manual_mode import run_manual_mode
from hybrid_mode import run_hybrid_mode

from PIL import Image, ImageDraw, ImageFont

class ScoreboardGenerator:
    def __init__(self, p1_name, p2_name, width=1920, height=1080):
        self.p1_name = p1_name
        self.p2_name = p2_name
        self.width = width
        self.height = height
        # Load fonts (Mac default location)
        try:
            self.font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
            self.font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
            self.font_game = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 150)
        except:
             # Fallback
            self.font_large = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_game = ImageFont.load_default()

    def create_scoreboard_image(self, p1_score, p2_score, p1_sets, p2_sets, output_path):
        # Create transparent image
        img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw Scoreboard Box (Bottom Center)
        box_w, box_h = 600, 150
        box_x = (self.width - box_w) // 2
        box_y = self.height - box_h - 50
        
        # Background
        draw.rectangle([box_x, box_y, box_x + box_w, box_y + box_h], fill=(0, 0, 0, 180))
        
        # Player Names
        draw.text((box_x + 20, box_y + 10), self.p1_name, font=self.font_small, fill="white")
        draw.text((box_x + box_w - 20, box_y + 10), self.p2_name, font=self.font_small, fill="white", anchor="ra")
        
        # Scores
        draw.text((box_x + 80, box_y + 60), str(p1_score), font=self.font_large, fill="yellow" if p1_score > p2_score else "white")
        draw.text((box_x + box_w - 80, box_y + 60), str(p2_score), font=self.font_large, fill="yellow" if p2_score > p1_score else "white", anchor="ra")
        
        # Sets
        draw.text((box_x + box_w // 2, box_y + 110), f"Sets: {p1_sets} - {p2_sets}", font=self.font_small, fill="gray", anchor="ma")
        
        img.save(output_path)

    def create_game_card(self, game_num, output_path):
        img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        text = f"GAME {game_num}"
        bbox = draw.textbbox((0, 0), text, font=self.font_game)
        draw.text(((self.width - bbox[2])/2, (self.height - bbox[3])/2), text, font=self.font_game, fill="white")
        img.save(output_path)

def process_video(events, args):
    if not events:
         return

    print("Generating overlays and processing rules...")
    
    # Init Logic
    game_num = 1
    p1_score = 0
    p2_score = 0
    p1_sets = 0
    p2_sets = 0
    
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
    processed_segments.append({"type": "card", "path": game_card_path, "duration": 3})
    
    for i, event in enumerate(events):
        # 1. State BEFORE the point (for display)
        overlay_path = os.path.join(temp_dir, f"score_{i}.png")
        gen.create_scoreboard_image(p1_score, p2_score, p1_sets, p2_sets, overlay_path)
        
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
                processed_segments.append({"type": "card", "path": card_path, "duration": 3})

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
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
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
                    "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", "-r", "30",
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
    
    # Cleanup (Optional)
    # shutil.rmtree(temp_dir)
    # os.remove(concat_list_path)

def main():
    args = parse_args()
    fps, duration = get_video_properties(args.input_file)
    print(f"Video detected: {duration:.2f}s @ {fps} fps")
    
    events = []
    if args.mode == "manual":
        events = run_manual_mode(args)
    elif args.mode == "hybrid":
        events = run_hybrid_mode(args)
        
    if events:
        process_video(events, args)
    else:
        print("No events recorded. Exiting.")

if __name__ == "__main__":
    main()
