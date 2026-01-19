from tt_video_editor.scoreboard.scoreboard_generator import ScoreboardGenerator
from PIL import Image
import os


def create_preview():
    # Sample Data
    p1_name = "Jonathan"
    p2_name = "Viet Dude"
    p1_sets, p2_sets = 2, 0
    p1_score, p2_score = 11, 9

    output_path = "scoreboard_preview.png"
    temp_path = "temp_preview.png"

    # Initialize Generator
    gen = ScoreboardGenerator(p1_name, p2_name)

    # 1. Create the transparent scoreboard image (with P1 timeout indicator)
    gen.create_scoreboard_image(
        p1_score, p2_score, p1_sets, p2_sets, temp_path, p1_timeout=True
    )

    # 2. Composite onto a white background (as requested)
    overlay = Image.open(temp_path).convert("RGBA")

    # Create white canvas
    canvas = Image.new("RGBA", overlay.size, (255, 255, 255, 255))

    # Paste overlay onto canvas
    canvas.alpha_composite(overlay)

    # Save final preview
    canvas.save(output_path)

    # Cleanup temp
    if os.path.exists(temp_path):
        os.remove(temp_path)

    print(f"Preview generated and saved to: {os.path.abspath(output_path)}")


if __name__ == "__main__":
    create_preview()
