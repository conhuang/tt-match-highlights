from PIL import Image, ImageDraw, ImageFont


class ScoreboardGenerator:
    def __init__(self, p1_name, p2_name, width=1920, height=1080):
        self.p1_name = p1_name
        self.p2_name = p2_name
        self.width = width
        self.height = height

        # Scale factor based on height (1080p as baseline)
        self.scale = height / 1080

        try:
            main_path = "/System/Library/Fonts/Menlo.ttc"
            # Scale font sizes based on resolution
            self.font_bold = ImageFont.truetype(main_path, int(48 * self.scale), index=1)
            self.font_main = ImageFont.truetype(main_path, int(40 * self.scale), index=0)
            self.font_small = ImageFont.truetype(main_path, int(24 * self.scale), index=0)
            self.font_game = ImageFont.truetype(main_path, int(120 * self.scale), index=1)
        except:
            # Fallback
            self.font_bold = ImageFont.load_default()
            self.font_main = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_game = ImageFont.load_default()

    def create_scoreboard_image(
        self, p1_score, p2_score, p1_sets, p2_sets, output_path, p1_timeout=False, p2_timeout=False
    ):
        # Create transparent image
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Scale all dimensions
        s = self.scale
        col_widths = [int(360 * s), int(80 * s), int(80 * s)]
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
        text_y_offset = int(12 * s)
        for i, (name, sets, points) in enumerate(
            [(self.p1_name, p1_sets, p1_score), (self.p2_name, p2_sets, p2_score)]
        ):
            y_offset = box_y + padding + i * row_height
            draw.text(
                (box_x + text_offset, y_offset + text_y_offset),
                name,
                font=self.font_main,
                fill="white",
            )

            set_box_x = box_x + col_widths[0]
            draw.text(
                (set_box_x + col_widths[1] / 2, y_offset + text_y_offset),
                str(sets),
                font=self.font_main,
                fill=(220, 220, 220),
                anchor="ma",
            )

            point_box_x = set_box_x + col_widths[1]
            draw.text(
                (point_box_x + col_widths[2] / 2, y_offset + text_y_offset),
                str(points),
                font=self.font_main,
                fill="white",
                anchor="ma",
            )

            # Timeout Indicator "T"
            has_timeout = p1_timeout if i == 0 else p2_timeout
            if has_timeout:
                # Place it right-aligned within the name column
                font_t = ImageFont.truetype(
                    "/System/Library/Fonts/Helvetica.ttc", int(28 * s), index=1
                )
                draw.text(
                    (box_x + col_widths[0] - int(12 * s), y_offset + int(40 * s)),
                    "T",
                    font=font_t,
                    fill=(255, 165, 0),
                    anchor="rs",
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
