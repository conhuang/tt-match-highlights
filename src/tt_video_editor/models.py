import os
import logging
import sys
import subprocess
import cv2
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class Video:
    def __init__(self, input_file):
        self.input_file = input_file
        self.fps, self.duration = self.get_video_properties()

    def get_video_properties(self):
        """Use ffprobe to get FPS and duration quickly."""
        if not os.path.exists(self.input_file):
            logger.error(f"Input file not found: {self.input_file}")
            sys.exit(1)

        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=r_frame_rate,duration,nb_frames",
                "-of",
                "json",
                self.input_file,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)

            stream = data["streams"][0]
            num, den = map(float, stream["r_frame_rate"].split("/"))
            fps = num / den if den != 0 else 0

            duration = float(stream.get("duration", 0))
            if duration == 0 and "nb_frames" in stream:
                duration = int(stream["nb_frames"]) / fps

            return fps, duration
        except Exception as e:
            logger.warning(f"ffprobe failed, falling back to cv2: {e}")

            cap = cv2.VideoCapture(self.input_file)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            cap.release()
            return fps, duration
        
        