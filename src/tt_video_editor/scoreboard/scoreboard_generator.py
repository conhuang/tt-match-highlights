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
        self.pkg_fonts_dir = pkg_fonts_dir
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

    THEME_PALETTES = {
        "dark-blue": {"fill": (10, 25, 60, 215), "outline": (255, 255, 255, 60)},
        "classic-black": {"fill": (15, 15, 18, 225), "outline": (255, 255, 255, 75)},
        "vibrant-red": {"fill": (80, 12, 18, 220), "outline": (255, 120, 120, 85)},
        "emerald-green": {"fill": (8, 48, 30, 220), "outline": (100, 220, 160, 85)},
        "cyber-purple": {"fill": (45, 15, 75, 220), "outline": (180, 100, 255, 85)},
    }

    SETS_COLOR_PALETTES = {
        "gold": (255, 200, 50),
        "silver": (220, 220, 220),
        "cyan": (90, 215, 255),
        "green": (50, 230, 140),
        "red": (255, 100, 100),
    }

    SETS_BG_PALETTES = {
        "transparent": None,
        "solid-dark": (0, 0, 0, 140),
        "gold-badge": (180, 135, 10, 130),
        "accent-blue": (30, 80, 180, 130),
        "subtle-glass": (255, 255, 255, 35),
    }

    def create_scoreboard_image(
        self,
        p1_score,
        p2_score,
        p1_sets,
        p2_sets,
        output_path,
        p1_timeout=False,
        p2_timeout=False,
        position="bottom-left",
        theme="dark-blue",
        scale_factor=1.0,
        sets_color="gold",
        border_style="rounded",
        font_style="modern",
        sets_bg="transparent",
    ):
        # Create transparent image
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Resolve Set Score Color
        parsed_sets_color = self.SETS_COLOR_PALETTES.get(sets_color, (255, 200, 50))
        if isinstance(sets_color, str) and sets_color.startswith("#"):
            try:
                hex_val = sets_color.lstrip('#')
                parsed_sets_color = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
            except Exception:
                parsed_sets_color = (255, 200, 50)

        # Scale all dimensions by base scale and custom scale_factor
        s = self.scale * max(0.6, min(float(scale_factor or 1.0), 1.6))
        col_widths = [int(self.name_col_width * max(0.6, min(float(scale_factor or 1.0), 1.6))), int(80 * s), int(80 * s)]
        row_height = int(64 * s)
        padding = int(16 * s)
        total_w = sum(col_widths)
        total_h = row_height * 2 + padding * 2

        margin_x = int(64 * s)
        margin_y = int(64 * s)

        # Calculate position coordinates
        pos = (position or "bottom-left").lower()
        if pos == "top-left":
            box_x = margin_x
            box_y = margin_y
        elif pos == "top-right":
            box_x = self.width - total_w - margin_x
            box_y = margin_y
        elif pos == "bottom-right":
            box_x = self.width - total_w - margin_x
            box_y = self.height - total_h - margin_y
        else:  # bottom-left (default)
            box_x = margin_x
            box_y = self.height - total_h - margin_y

        # Resolve Theme Colors
        theme_colors = self.THEME_PALETTES.get(theme, self.THEME_PALETTES["dark-blue"])

        # Calculate Corner Radius based on border_style (rounded vs sharp edge)
        corner_radius = 0 if (border_style or "rounded").lower() == "sharp" else int(14 * (scale_factor or 1.0))

        # Background Rectangle
        draw.rounded_rectangle(
            [box_x, box_y, box_x + total_w, box_y + total_h],
            radius=corner_radius,
            fill=theme_colors["fill"],
            outline=theme_colors["outline"],
            width=2,
        )

        # Draw Set Column Highlight Background if configured (Edge-to-Edge full height)
        parsed_sets_bg = self.SETS_BG_PALETTES.get(sets_bg, None)
        if parsed_sets_bg:
            sep1_x = box_x + col_widths[0]
            draw.rectangle(
                [sep1_x + 1, box_y + 1, sep1_x + col_widths[1] - 1, box_y + total_h - 1],
                fill=parsed_sets_bg
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

        # Resolve Selected Font File from bundled package directory
        FONT_MAP = {
            "modern": "Scoreboard-Bold.ttf",
            "condensed": "Scoreboard-Condensed.ttf",
            "serif": "Scoreboard-Serif.ttf",
            "monospace": "Scoreboard-Mono.ttf",
        }
        font_filename = FONT_MAP.get((font_style or "modern").lower(), "Scoreboard-Bold.ttf")
        selected_font_path = os.path.join(self.pkg_fonts_dir, font_filename)
        if not os.path.exists(selected_font_path):
            selected_font_path = self.font_bold_path

        custom_font_main = self._load_font(selected_font_path, int(40 * s))
        max_text_w = col_widths[0] - int(48 * s)
        p1_custom_font = self._find_fitting_font(self.p1_name, max_text_w, selected_font_path)
        p2_custom_font = self._find_fitting_font(self.p2_name, max_text_w, selected_font_path)

        text_offset = int(16 * s)
        for i, (name, font, sets, points) in enumerate(
            [
                (self.p1_name, p1_custom_font, p1_sets, p1_score),
                (self.p2_name, p2_custom_font, p2_sets, p2_score),
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
                font=custom_font_main,
                fill=parsed_sets_color,
                anchor="mm",
            )

            # Draw points score (vertical middle-aligned)
            point_box_x = set_box_x + col_widths[1]
            draw.text(
                (point_box_x + col_widths[2] / 2, y_offset + row_height / 2),
                str(points),
                font=custom_font_main,
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
