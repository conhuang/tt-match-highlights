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

        # Determine the name column width
        min_col_w = int(360 * s)
        max_col_w = int(500 * s)
        
        p1_w_base = self._get_text_width(self.p1_name, self.font_main)
        p2_w_base = self._get_text_width(self.p2_name, self.font_main)
        
        padding_for_text = int(48 * s)
        needed_w = max(p1_w_base, p2_w_base) + padding_for_text
        
        self.name_col_width = max(min_col_w, min(needed_w, max_col_w))
        
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
        "dark-blue": {
            "name_bg": (18, 28, 50, 215),
            "set_bg": (40, 55, 85, 220),
            "point_bg": (30, 42, 68, 215),
            "accent_color": (55, 160, 170, 255),
            "fill": (10, 25, 60, 215),
            "outline": (255, 255, 255, 60)
        },
        "classic-black": {
            "name_bg": (25, 25, 30, 225),
            "set_bg": (42, 42, 50, 225),
            "point_bg": (15, 15, 18, 235),
            "accent_color": (180, 190, 205, 255),
            "fill": (15, 15, 18, 225),
            "outline": (255, 255, 255, 75)
        },
        "vibrant-red": {
            "name_bg": (80, 12, 18, 220),
            "set_bg": (115, 20, 30, 225),
            "point_bg": (50, 8, 12, 235),
            "accent_color": (255, 100, 100, 255),
            "fill": (80, 12, 18, 220),
            "outline": (255, 120, 120, 85)
        },
        "emerald-green": {
            "name_bg": (8, 48, 30, 220),
            "set_bg": (15, 72, 45, 225),
            "point_bg": (6, 32, 20, 235),
            "accent_color": (50, 220, 140, 255),
            "fill": (8, 48, 30, 220),
            "outline": (100, 220, 160, 85)
        },
        "cyber-purple": {
            "name_bg": (45, 15, 75, 220),
            "set_bg": (70, 22, 112, 225),
            "point_bg": (28, 10, 50, 235),
            "accent_color": (210, 80, 255, 255),
            "fill": (45, 15, 75, 220),
            "outline": (180, 100, 255, 85)
        },
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

    ARTWORK_STYLES = {
        "classic": "Classic",
        "simple": "Simple"
    }

    def compute_table_tennis_server(self, p1_score, p2_score, p1_sets, p2_sets, first_server="player1"):
        game_num = p1_sets + p2_sets + 1
        if game_num % 2 == 1:
            game_first = first_server
        else:
            game_first = "player2" if first_server == "player1" else "player1"

        total_pts = p1_score + p2_score
        if p1_score >= 10 and p2_score >= 10:
            switches = total_pts - 20
            is_game_first = (switches % 2 == 0)
        else:
            switches = total_pts // 2
            is_game_first = (switches % 2 == 0)

        return game_first if is_game_first else ("player2" if game_first == "player1" else "player1")

    def create_scoreboard_image(
        self,
        p1_score,
        p2_score,
        p1_sets,
        p2_sets,
        output_path,
        p1_timeout=False,
        p2_timeout=False,
        serving_player=None,
        first_server="player1",
        artwork_style="classic",
        position="bottom-left",
        theme="dark-blue",
        scale_factor=1.0,
        sets_color="gold",
        border_style="rounded",
        font_style="modern",
        sets_bg="transparent",
    ):
        """Create a scoreboard overlay image choosing between Classic and Simple artwork styles."""
        style_clean = (artwork_style or "classic").lower()
        if style_clean in ["simple", "classic-card"]:
            return self._draw_simple_artwork(
                p1_score, p2_score, p1_sets, p2_sets, output_path,
                p1_timeout=p1_timeout, p2_timeout=p2_timeout,
                serving_player=serving_player, first_server=first_server,
                position=position, theme=theme, scale_factor=scale_factor,
                sets_color=sets_color, border_style=border_style,
                font_style=font_style, sets_bg=sets_bg
            )
        else:
            return self._draw_classic_artwork(
                p1_score, p2_score, p1_sets, p2_sets, output_path,
                p1_timeout=p1_timeout, p2_timeout=p2_timeout,
                serving_player=serving_player, first_server=first_server,
                position=position, theme=theme, scale_factor=scale_factor,
                sets_color=sets_color, border_style=border_style,
                font_style=font_style, sets_bg=sets_bg
            )

    def _draw_classic_artwork(
        self, p1_score, p2_score, p1_sets, p2_sets, output_path,
        p1_timeout=False, p2_timeout=False, serving_player=None, first_server="player1",
        position="bottom-left", theme="dark-blue", scale_factor=1.0, sets_color="gold",
        border_style="rounded", font_style="modern", sets_bg="transparent"
    ):
        """Artwork 1: Classic Broadcast Multi-Panel Artwork."""
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        parsed_sets_color = self.SETS_COLOR_PALETTES.get(sets_color, (255, 200, 50))
        if isinstance(sets_color, str) and sets_color.startswith("#"):
            try:
                hex_val = sets_color.lstrip('#')
                parsed_sets_color = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
            except Exception:
                parsed_sets_color = (255, 200, 50)

        theme_colors = self.THEME_PALETTES.get(theme, self.THEME_PALETTES["dark-blue"])
        parsed_sets_bg = self.SETS_BG_PALETTES.get(sets_bg, None)

        active_server = serving_player
        if not active_server:
            active_server = self.compute_table_tennis_server(p1_score, p2_score, p1_sets, p2_sets, first_server)

        sf = max(0.6, min(float(scale_factor or 1.0), 1.6))
        s = self.scale * sf

        accent_w = int(5 * s)
        name_col_w = int(self.name_col_width * sf)
        set_col_w = int(72 * s)
        point_col_w = int(80 * s)
        row_h = int(58 * s)
        corner_r = 0 if (border_style or "rounded").lower() == "sharp" else int(10 * s)

        total_w = accent_w + name_col_w + set_col_w + point_col_w
        total_h = row_h * 2

        margin_x = int(64 * s)
        margin_y = int(64 * s)

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
        else:
            box_x = margin_x
            box_y = self.height - total_h - margin_y

        row_bg = theme_colors["name_bg"]
        set_bg = theme_colors["set_bg"]
        point_bg = theme_colors["point_bg"]
        accent_color = theme_colors["accent_color"]
        divider_color = (255, 255, 255, 30)

        if parsed_sets_bg:
            set_bg = parsed_sets_bg

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

        name_font_path = selected_font_path
        max_name_text_w = name_col_w - int(56 * s)
        p1_name_font = self._find_fitting_font(self.p1_name, max_name_text_w, name_font_path)
        p2_name_font = self._find_fitting_font(self.p2_name, max_name_text_w, name_font_path)

        set_font = self._load_font(selected_font_path, int(34 * s))
        point_font = self._load_font(selected_font_path, int(40 * s))
        t_font = self._load_font(self.font_bold_path, int(14 * s))

        panel = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        panel_draw = ImageDraw.Draw(panel)

        set_area_x = box_x + accent_w + name_col_w
        point_area_x = set_area_x + set_col_w

        panel_draw.rectangle([box_x, box_y, box_x + total_w, box_y + total_h], fill=row_bg)
        panel_draw.rectangle([box_x, box_y, box_x + accent_w, box_y + total_h], fill=accent_color)
        panel_draw.rectangle([set_area_x, box_y, set_area_x + set_col_w, box_y + total_h], fill=set_bg)
        panel_draw.rectangle([point_area_x, box_y, box_x + total_w, box_y + total_h], fill=point_bg)

        if corner_r > 0:
            mask = Image.new("L", (self.width, self.height), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([box_x, box_y, box_x + total_w, box_y + total_h], radius=corner_r, fill=255)
            panel.putalpha(Image.fromarray(
                __import__('numpy').minimum(
                    __import__('numpy').array(panel.split()[3]),
                    __import__('numpy').array(mask)
                )
            ))
        img.alpha_composite(panel)

        draw.rounded_rectangle([box_x, box_y, box_x + total_w, box_y + total_h], radius=corner_r, outline=(255, 255, 255, 30), width=1)

        divider_y = box_y + row_h
        draw.line([box_x + accent_w + int(8 * s), divider_y, box_x + total_w - int(8 * s), divider_y], fill=divider_color, width=1)

        line_pad = int(10 * s)
        draw.line([set_area_x, box_y + line_pad, set_area_x, box_y + total_h - line_pad], fill=divider_color, width=1)
        draw.line([point_area_x, box_y + line_pad, point_area_x, box_y + total_h - line_pad], fill=divider_color, width=1)

        players = [
            (self.p1_name, p1_name_font, p1_sets, p1_score, p1_timeout, active_server in ["player1", self.p1_name, 1]),
            (self.p2_name, p2_name_font, p2_sets, p2_score, p2_timeout, active_server in ["player2", self.p2_name, 2]),
        ]

        for i, (name, name_font, sets, points, has_timeout, is_serving) in enumerate(players):
            ry = box_y + i * row_h
            center_y = ry + row_h / 2
            text_left = box_x + accent_w + int(24 * s)

            # Serving triangle matching accent color
            if is_serving:
                tri_size = int(7 * s)
                tri_x = box_x + total_w + int(6 * s)
                draw.polygon(
                    [
                        (tri_x + tri_size, center_y - tri_size),
                        (tri_x, center_y),
                        (tri_x + tri_size, center_y + tri_size),
                    ],
                    fill=accent_color,
                )

            # Player Name
            draw.text((text_left, center_y), name, font=name_font, fill=(235, 235, 240, 255), anchor="lm")

            # Timeout Indicator "T"
            if has_timeout:
                tb_w = int(18 * s)
                tb_h = int(18 * s)
                tb_x = set_area_x - tb_w - int(8 * s)
                tb_y = center_y - tb_h / 2
                draw.rounded_rectangle([tb_x, tb_y, tb_x + tb_w, tb_y + tb_h], radius=int(3 * s), fill=(255, 195, 0, 240))
                draw.text((tb_x + tb_w / 2, center_y), "T", font=t_font, fill=(20, 20, 20, 255), anchor="mm")

            # Set Score
            draw.text((set_area_x + set_col_w / 2, center_y), str(sets), font=set_font, fill=parsed_sets_color, anchor="mm")

            # Point Score
            draw.text((point_area_x + point_col_w / 2, center_y), str(points), font=point_font, fill=(255, 255, 255, 255), anchor="mm")

        img.save(output_path)

    def _draw_simple_artwork(
        self, p1_score, p2_score, p1_sets, p2_sets, output_path,
        p1_timeout=False, p2_timeout=False, serving_player=None, first_server="player1",
        position="bottom-left", theme="dark-blue", scale_factor=1.0, sets_color="gold",
        border_style="rounded", font_style="modern", sets_bg="transparent"
    ):
        """Artwork 2: Simple Unified Card Artwork."""
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        parsed_sets_color = self.SETS_COLOR_PALETTES.get(sets_color, (255, 200, 50))
        if isinstance(sets_color, str) and sets_color.startswith("#"):
            try:
                hex_val = sets_color.lstrip('#')
                parsed_sets_color = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
            except Exception:
                parsed_sets_color = (255, 200, 50)

        theme_colors = self.THEME_PALETTES.get(theme, self.THEME_PALETTES["dark-blue"])
        parsed_sets_bg = self.SETS_BG_PALETTES.get(sets_bg, None)

        active_server = serving_player
        if not active_server:
            active_server = self.compute_table_tennis_server(p1_score, p2_score, p1_sets, p2_sets, first_server)

        sf = max(0.6, min(float(scale_factor or 1.0), 1.6))
        s = self.scale * sf

        col_widths = [int(self.name_col_width * sf), int(80 * s), int(80 * s)]
        row_height = int(64 * s)
        padding = int(16 * s)
        total_w = sum(col_widths)
        total_h = row_height * 2 + padding * 2

        margin_x = int(64 * s)
        margin_y = int(64 * s)

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
        else:
            box_x = margin_x
            box_y = self.height - total_h - margin_y

        corner_radius = 0 if (border_style or "rounded").lower() == "sharp" else int(14 * s)

        # Background Card
        draw.rounded_rectangle(
            [box_x, box_y, box_x + total_w, box_y + total_h],
            radius=corner_radius,
            fill=theme_colors["fill"],
            outline=theme_colors["outline"],
            width=2,
        )

        # Draw Set Column Highlight Background if configured
        if parsed_sets_bg:
            sep1_x = box_x + col_widths[0]
            draw.rectangle(
                [sep1_x + 1, box_y + 1, sep1_x + col_widths[1] - 1, box_y + total_h - 1],
                fill=parsed_sets_bg
            )

        # Draw Inner Separator Lines
        line_color = (255, 255, 255, 40)
        line_padding = int(12 * s)
        sep1_x = box_x + col_widths[0]
        draw.line([sep1_x, box_y + line_padding, sep1_x, box_y + total_h - line_padding], fill=line_color, width=1)

        sep2_x = sep1_x + col_widths[1]
        draw.line([sep2_x, box_y + line_padding, sep2_x, box_y + total_h - line_padding], fill=line_color, width=1)

        # Resolve Fonts
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
        t_font = self._load_font(self.font_bold_path, int(24 * s))
        max_text_w = col_widths[0] - int(48 * s)
        p1_custom_font = self._find_fitting_font(self.p1_name, max_text_w, selected_font_path)
        p2_custom_font = self._find_fitting_font(self.p2_name, max_text_w, selected_font_path)

        text_offset = int(16 * s)
        players = [
            (self.p1_name, p1_custom_font, p1_sets, p1_score, p1_timeout, active_server in ["player1", self.p1_name, 1]),
            (self.p2_name, p2_custom_font, p2_sets, p2_score, p2_timeout, active_server in ["player2", self.p2_name, 2]),
        ]

        for i, (name, font, sets, points, has_timeout, is_serving) in enumerate(players):
            y_offset = box_y + padding + i * row_height
            row_center_y = y_offset + row_height / 2

            # Serve Dot (🟡) next to player name
            name_x = box_x + text_offset
            if is_serving:
                dot_r = int(5 * s)
                draw.ellipse([name_x, row_center_y - dot_r, name_x + dot_r * 2, row_center_y + dot_r], fill=(255, 215, 0, 255))
                name_x += int(16 * s)

            # Player Name
            draw.text((name_x, y_offset + int(12 * s)), name, font=font, fill="white")

            # Set Score
            set_box_x = box_x + col_widths[0]
            draw.text((set_box_x + col_widths[1] / 2, y_offset + int(12 * s)), str(sets), font=custom_font_main, fill=parsed_sets_color, anchor="ma")

            # Point Score
            point_box_x = set_box_x + col_widths[1]
            draw.text((point_box_x + col_widths[2] / 2, y_offset + int(12 * s)), str(points), font=custom_font_main, fill="white", anchor="ma")

            # Timeout Indicator "T"
            if has_timeout:
                draw.text((box_x + col_widths[0] - int(14 * s), y_offset + int(38 * s)), "T", font=t_font, fill=(255, 195, 0), anchor="rs")

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
