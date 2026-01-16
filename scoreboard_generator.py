from PIL import Image, ImageDraw, ImageFont

class ScoreboardGenerator:
    def __init__(self, p1_name, p2_name, width=1920, height=1080):
        self.p1_name = p1_name
        self.p2_name = p2_name
        self.width = width
        self.height = height
        # Load fonts (Directly use Helvetica.ttc)
        try:
            main_path = "/System/Library/Fonts/Helvetica.ttc"
            # index 1 is Bold, index 0 is Regular in macOS Helvetica.ttc
            self.font_bold = ImageFont.truetype(main_path, 60, index=1)
            self.font_main = ImageFont.truetype(main_path, 50, index=0)
            self.font_small = ImageFont.truetype(main_path, 30, index=0)
            self.font_game = ImageFont.truetype(main_path, 150, index=1)
        except:
             # Fallback
            self.font_bold = ImageFont.load_default()
            self.font_main = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_game = ImageFont.load_default()

    def create_scoreboard_image(self, p1_score, p2_score, p1_sets, p2_sets, output_path):
        # Create transparent image
        img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Grid Configuration
        col_widths = [450, 100, 100]
        row_height = 80
        padding = 20
        total_w = sum(col_widths)
        total_h = row_height * 2 + padding * 2
        
        box_x = 80
        box_y = self.height - total_h - 80
        
        # Background: Dark Blue
        draw.rounded_rectangle([box_x, box_y, box_x + total_w, box_y + total_h], 
                               radius=15, fill=(10, 25, 60, 210), outline=(255, 255, 255, 60), width=2)
        
        # Draw Separator Lines
        line_color = (255, 255, 255, 40)
        # Line 1: Between Name and Sets
        sep1_x = box_x + col_widths[0]
        draw.line([sep1_x, box_y + 15, sep1_x, box_y + total_h - 15], fill=line_color, width=1)
        # Line 2: Between Sets and Points
        sep2_x = sep1_x + col_widths[1]
        draw.line([sep2_x, box_y + 15, sep2_x, box_y + total_h - 15], fill=line_color, width=1)

        for i, (name, sets, points) in enumerate([
            (self.p1_name, p1_sets, p1_score),
            (self.p2_name, p2_sets, p2_score)
        ]):
            y_offset = box_y + padding + i * row_height
            draw.text((box_x + 20, y_offset + 15), name, font=self.font_main, fill="white")
            
            set_box_x = box_x + col_widths[0]
            draw.text((set_box_x + col_widths[1]/2, y_offset + 15), str(sets), 
                      font=self.font_bold, fill=(220, 220, 220), anchor="ma")
            
            point_box_x = set_box_x + col_widths[1]
            is_leading = (i == 0 and p1_score > p2_score) or (i == 1 and p2_score > p1_score)
            fill_color = (255, 215, 0) if is_leading else "white"
            draw.text((point_box_x + col_widths[2]/2, y_offset + 15), str(points), 
                      font=self.font_bold, fill=fill_color, anchor="ma")

        # Labels removed per user request
        img.save(output_path)

    def create_game_card(self, game_num, output_path):
        img = Image.new('RGB', (self.width, self.height), (10, 10, 15))
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, self.width - 50, self.height - 50], outline=(50, 50, 70), width=3)
        text = f"GAME {game_num}"
        bbox = draw.textbbox((0, 0), text, font=self.font_game)
        draw.text(((self.width - bbox[2])/2, (self.height - (bbox[3]-bbox[1]))/2), 
                  text, font=self.font_game, fill=(255, 255, 255))
        img.save(output_path)
