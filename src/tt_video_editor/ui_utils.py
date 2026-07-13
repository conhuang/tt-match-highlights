import cv2


def draw_status_overlay(frame, lines, font_scale=0.5):
    """
    Draw status text overlay on a video frame.

    Args:
        frame: OpenCV frame (numpy array)
        lines: List of strings or (text, color_bgr) tuples.
               If a plain string is given, white (255, 255, 255) is used.
        font_scale: Font scale for cv2.putText
    """
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = max(1, int(font_scale * 2))
    y_offset = 30

    for line in lines:
        if isinstance(line, tuple):
            text, color = line
        else:
            text = line
            color = (255, 255, 255)

        # Draw black outline for readability
        cv2.putText(frame, text, (10, y_offset), font, font_scale, (0, 0, 0), thickness + 2)
        # Draw colored text
        cv2.putText(frame, text, (10, y_offset), font, font_scale, color, thickness)

        y_offset += int(30 * font_scale + 15)
