"""Standalone proxy creation script for fast-seeking video editing."""

import os
import subprocess
import sys


def create_proxy(input_file, output_file=None):
    """Create a fast-seeking proxy file for editing (540p, all-keyframe)."""
    if output_file is None:
        base = os.path.splitext(input_file)[0]
        output_file = f"{base}_proxy.mp4"

    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    if os.path.exists(output_file):
        print(f"Proxy already exists: {output_file}")
        print("Delete it first if you want to re-create.")
        return output_file

    print(f"Creating fast-seek proxy...")
    print(f"  Input:  {input_file}")
    print(f"  Output: {output_file}")
    print(f"  This may take a few minutes for long videos.")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_file,
        "-vf",
        "scale=960:-2",  # 540p width
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "28",
        "-g",
        "1",  # Every frame is a keyframe = instant seeking
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        output_file,
    ]

    # Run with visible progress
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print(f"\nProxy created: {output_file}")
        return output_file
    else:
        print(f"Proxy creation failed")
        sys.exit(1)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Create fast-seeking proxy for video editing")
    parser.add_argument("input", help="Input video file (e.g., video.MOV)")
    parser.add_argument("-o", "--output", help="Output proxy file (default: input_proxy.mp4)")
    args = parser.parse_args()

    create_proxy(args.input, args.output)


if __name__ == "__main__":
    main()
