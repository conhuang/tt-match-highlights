import cv2
import numpy as np

def draw_status_overlay(frame, lines, font_scale=1.2, thickness=2, box_alpha=0.6):
    """
    Draws a semi-transparent box with multiple lines of text at the top left.
    Args:
        frame: The video frame to draw on.
        lines: List of tuples (text, color) or just strings (default white).
        font_scale: Base font scale.
        thickness: Font thickness.
        box_alpha: Transparency of the background box.
    """
    if not lines:
        return
        
    # Standardize lines to (text, color)
    standard_lines = []
    for line in lines:
        if isinstance(line, tuple):
            standard_lines.append(line)
        else:
            standard_lines.append((line, (255, 255, 255))) # Default white
            
    # Calculate box dimensions based on text and scale
    padding = 20
    line_spacing = int(font_scale * 45)
    
    max_w = 0
    for text, color in standard_lines:
        size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        max_w = max(max_w, size[0])
        
    box_w = max_w + padding * 2
    box_h = len(standard_lines) * line_spacing + padding * 2
    
    box_x1, box_y1 = 30, 20
    box_x2, box_y2 = box_x1 + box_w, box_y1 + box_h
    
    # Draw Background
    overlay = frame.copy()
    cv2.rectangle(overlay, (box_x1, box_y1), (box_x2, box_y2), (0, 0, 0), -1)
    cv2.addWeighted(overlay, box_alpha, frame, 1 - box_alpha, 0, frame)
    
    # Draw Text
    for i, (text, color) in enumerate(standard_lines):
        y = box_y1 + padding + (i + 1) * line_spacing - int(line_spacing * 0.3)
        cv2.putText(frame, text, (box_x1 + padding, y), 
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)
