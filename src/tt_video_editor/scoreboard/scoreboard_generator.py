from PIL import Image, ImageDraw, ImageFont
import os


class ScoreboardGenerator:
    def __init__(self, p1_name, p2_name, width=1920, height=1080):
        # Scale factor based on height (1080p as baseline)
        self.scale = height / 1080
        s = self.scale
        self.width = width
        self.height = height

        # Enforce character limit of 22 characters
        CHAR_LIMIT = 22
        def limit_name(name):
            if not name:
                return ""
            name = name.strip()
            if len(name) > CHAR_LIMIT:
                return name[:CHAR_LIMIT - 3] + "..."
            return name

        self.p1_name = limit_name(p1_name)
        self.p2_name = limit_name(p2_name)

        # Resolve bundled font paths in tt_video_editor package
        pkg_fonts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fonts"))
        bundled_bold = os.path.join(pkg_fonts_dir, "Scoreboard-Bold.ttf")
        bundled_regular = os.path.join(pkg_fonts_dir, "Scoreboard-Regular.ttf")

        font_bold_path = bundled_bold if os.path.exists(bundled_bold) else "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        font_regular_path = bundled_regular if os.path.exists(bundled_regular) else "/System/Library/Fonts/Supplemental/Arial.ttf"

        self.font_bold_path = font_bold_path
        self.font_regular_path = font_regular_path

        # Load baseline fonts safely
        self.font_bold = self._load_font(font_bold_path, int(48 * s))
        self.font_main = self._load_font(font_regular_path, int(40 * s))
        self.font_small = self._load_font(font_regular_path, int(24 * s))
        self.font_game = self._load_font(font_bold_path, int(120 * s))
        self.font_t = self._load_font(font_bold_path, int(28 * s))

        # Determine the name column width and custom fonts for each player name
        # Minimum name column width is 360 * s, maximum is 500 * s
        min_col_w = int(360 * s)
        max_col_w = int(500 * s)
        
        # We will dynamically measure the width of the names at baseline font (size 40 * s)
        # to decide if we need to expand the column width.
        p1_w_base = self._get_text_width(self.p1_name, self.font_main)
        p2_w_base = self._get_text_width(self.p2_name, self.font_main)
        
        # Optimal column width (with 48 * s padding for name + timeout letter T space)
        padding_for_text = int(48 * s)
        needed_w = max(p1_w_base, p2_w_base) + padding_for_text
        
        # Clamp between min_col_w and max_col_w
        self.name_col_width = max(min_col_w, min(needed_w, max_col_w))
        
        # Find best font for p1_name and p2_name to fit within (self.name_col_width - padding_for_text)
        max_text_w = self.name_col_width - padding_for_text
        self.p1_font = self._find_fitting_font(self.p1_name, max_text_w, font_regular_path)
        self.p2_font = self._find_fitting_font(self.p2_name, max_text_w, font_regular_path)

    def _load_font(self, font_path, size):
        if not font_path or not os.path.exists(font_path):
            return ImageFont.load_default()
        try:
            if font_path.endswith(".ttc"):
                return ImageFont.truetype(font_path, size, index=0)
            return ImageFont.truetype(font_path, size)
        except Exception:
            return ImageFont.load_default()

    def _get_text_width(self, text, font):
        # Create a dummy image to measure text width
        img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0] 

    def _find_fitting_font(self, name, max_width, font_path):
        s = self.scale
        base_size = int(40 * s)
        min_size = int(20 * s)
        
        for size in range(base_size, min_size - 1, -2):
            font = self._load_font(font_path, size)
            w = self._get_text_width(name, font)
            if w <= max_width:
                return font
                
        return self._load_font(font_path, min_size)

    def create_scoreboard_image(
        self, p1_score, p2_score, p1_sets, p2_sets, output_path, p1_timeout=False, p2_timeout=False
    ):
        # Create transparent image
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Scale all dimensions
        s = self.scale
        col_widths = [self.name_col_width, int(80 * s), int(80 * s)]
        row_height = int(64 * s)
        padding = int(16 * s)
        total_w = sum(col_widths)
        total_h = row_height * 2 + padding * 2

        box_x = int(64 * s)
        box_y = self.height - total_h - int(64 * s)

        # Background: Dark Blue
        draw.rounded_rectangle(
            [box_x, box_y, box_x + total_w, box_y + total_h],
            radius=12,
            fill=(10, 25, 60, 210),
            outline=(255, 255, 255, 60),
            width=2,
        )

        # Draw Separator Lines
        line_color = (255, 255, 255, 40)
        line_padding = int(12 * s)
        # Line 1: Between Name and Sets
        sep1_x = box_x + col_widths[0]
        draw.line(
            [sep1_x, box_y + line_padding, sep1_x, box_y + total_h - line_padding],
            fill=line_color,
            width=1,
        )
        # Line 2: Between Sets and Points
        sep2_x = sep1_x + col_widths[1]
        draw.line(
            [sep2_x, box_y + line_padding, sep2_x, box_y + total_h - line_padding],
            fill=line_color,
            width=1,
        )

        text_offset = int(16 * s)
        for i, (name, font, sets, points) in enumerate(
            [
                (self.p1_name, self.p1_font, p1_sets, p1_score),
                (self.p2_name, self.p2_font, p2_sets, p2_score),
            ]
        ):
            y_offset = box_y + padding + i * row_height
          
            # Draw player name (vertical middle-aligned)

            draw.text(
                (box_x + text_offset + 10, y_offset + row_height / 2),
                name,
                font=font,
                fill="white",
                anchor="lm",
            )

            # Draw sets score (vertical middle-aligned)
            set_box_x = box_x + col_widths[0]
            draw.text(
                (set_box_x + col_widths[1] / 2, y_offset + row_height / 2),
                str(sets),
                font=self.font_main,
                fill=(220, 220, 220),
                anchor="mm",
            )

            # Draw points score (vertical middle-aligned)
            point_box_x = set_box_x + col_widths[1]
            draw.text(
                (point_box_x + col_widths[2] / 2, y_offset + row_height / 2),
                str(points),
                font=self.font_main,
                fill="white",
                anchor="mm",
            )

            # Timeout Indicator "T"
            has_timeout = p1_timeout if i == 0 else p2_timeout
            if has_timeout:
                # Place it right-aligned within the name column
                draw.text(
                    (box_x + col_widths[0] - int(12 * s), y_offset + row_height / 2),
                    "T",
                    font=self.font_t,
                    fill=(255, 165, 0),
                    anchor="rm",
                )

        # Labels removed per user request
        img.save(output_path)

    def create_game_card(self, game_num, output_path):
        img = Image.new("RGB", (self.width, self.height), (10, 10, 15))
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, self.width - 50, self.height - 50], outline=(50, 50, 70), width=3)
        text = f"GAME {game_num}"
        bbox = draw.textbbox((0, 0), text, font=self.font_game)
        draw.text(
            ((self.width - bbox[2]) / 2, (self.height - (bbox[3] - bbox[1])) / 2),
            text,
            font=self.font_game,
            fill=(255, 255, 255),
        )
        img.save(output_path)
