"""
Prototype: Table Tennis Rally & Dead-Time Detector using Google AI Studio (Gemini API).

This script uploads a table tennis match video to Google AI Studio via Gemini API,
uses Gemini's multimodal video understanding to detect all active rallies,
and outputs a JSON file with start and end timestamps for dead-time removal.

Usage:
    export GEMINI_API_KEY="your-api-key-here"
    python scripts/prototype_gemini_rally_detector.py path/to/match.mp4
"""

import sys
import os
import json
import time
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/prototype_gemini_rally_detector.py <video_path>")
        sys.exit(1)

    video_path = sys.argv[1]
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at {video_path}")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.")
        print("Please set it via: export GEMINI_API_KEY='your_google_ai_studio_key'")
        sys.exit(1)

    print(f"=== Table Tennis Gemini Rally Detector Prototype ===")
    print(f"Video File: {video_path}")
    
    # Try importing google.genai or google.generativeai
    try:
        from google import genai
        from google.genai import types
        USE_NEW_SDK = True
    except ImportError:
        try:
            import google.generativeai as genai
            USE_NEW_SDK = False
        except ImportError:
            print("\nError: Google GenAI SDK not installed.")
            print("Please install via: pip install google-genai")
            sys.exit(1)

    print("Uploading video to Google AI Studio...")
    start_time = time.time()

    if USE_NEW_SDK:
        client = genai.Client(api_key=api_key)
        video_file = client.files.upload(file=video_path)
        print(f"Uploaded as {video_file.name}. Waiting for processing...")
        
        # Poll file processing status
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = client.files.get(name=video_file.name)
            print(".", end="", flush=True)
        print()

        if video_file.state.name == "FAILED":
            raise ValueError(f"File processing failed: {video_file.error.message}")

        prompt = """
        You are a world-class table tennis match video analyst.
        Watch this table tennis match video carefully and identify every active rally.
        
        Rules:
        1. A rally starts when a player tosses or strikes the ball to serve.
        2. A rally ends when the ball goes out of bounds, hits the net, or play stops.
        3. Exclude all dead time (e.g. ball retrieval, wiping towel, player walking between points, waiting).
        4. Output a JSON list of objects, each containing:
           - "start_time": float timestamp in seconds when rally starts
           - "end_time": float timestamp in seconds when rally ends
           - "point_summary": brief description (e.g., "Forehand loop winner", "Net serve let", "Backhand error")
        """

        print("Requesting rally detection from Gemini (gemini-2.5-flash)...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[video_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        result_text = response.text

    else:
        genai.configure(api_key=api_key)
        video_file = genai.upload_file(path=video_path)
        print(f"Uploaded as {video_file.name}. Waiting for processing...")
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)
            print(".", end="", flush=True)
        print()

        prompt = """
        Identify all active table tennis rallies in this video. 
        Output JSON list with "start_time" (float seconds), "end_time" (float seconds), and "description".
        Exclude dead time (towel breaks, ball picking, waiting).
        """
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([video_file, prompt])
        result_text = response.text

    elapsed = time.time() - start_time
    print(f"Analysis completed in {elapsed:.1f} seconds!")

    try:
        rallies = json.loads(result_text)
        print(f"\nSuccessfully detected {len(rallies)} rallies:")
        print(json.dumps(rallies, indent=2))
        
        output_json = Path(video_path).stem + "_gemini_rallies.json"
        with open(output_json, "w") as f:
            json.dump(rallies, f, indent=2)
        print(f"\nSaved detected rallies to: {output_json}")
    except json.JSONDecodeError:
        print("\nRaw Gemini Output:")
        print(result_text)

if __name__ == "__main__":
    main()
