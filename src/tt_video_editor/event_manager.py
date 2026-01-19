import json
import os
import logging

logger = logging.getLogger(__name__)

def save_events(events, filepath):
    """
    Saves a list of event dictionaries to a JSON file.
    """
    try:
        with open(filepath, 'w') as f:
            json.dump(events, f, indent=4)
        print(f"Events saved to: {filepath}")
    except Exception as e:
        logger.error(f"Failed to save events to {filepath}: {e}")

def load_events(filepath):
    """
    Loads a list of event dictionaries from a JSON file.
    """
    if not os.path.exists(filepath):
        logger.error(f"Event file not found: {filepath}")
        return None
        
    try:
        with open(filepath, 'r') as f:
            events = json.load(f)
        print(f"Loaded {len(events)} events from: {filepath}")
        return events
    except Exception as e:
        logger.error(f"Failed to load events from {filepath}: {e}")
        return None

def get_default_event_path(input_video_path):
    """
    Generates a default JSON path based on the input video filename.
    Example: video.mp4 -> video_events.json
    """
    base = os.path.splitext(input_video_path)[0]
    return f"{base}_events.json"
