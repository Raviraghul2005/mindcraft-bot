"""
services/image_overlay.py — Add quote text onto the generated image.
Short quotes → BIG, BOLD, eye-catching text.
"""
import textwrap
from PIL import Image, ImageDraw, ImageFont
import config


def overlay_quote(image_path, quote, output_path=None):
    """
    Overlay a short, punchy quote onto the image.
    - Resizes to 1080x1350 (4:5 Instagram)
    - BIG bold font — designed for short 1-2 line quotes
    - White text with strong black outline for max readability
    - Text centered in lower third of image
    
    Returns the output image path.
    """
    if output_path is None:
        output_path = config.QUOTE_IMAGE_FILE

    # Open and resize to Instagram Reels dimensions
    img = Image.open(image_path).convert("RGB")
    img = img.resize((config.VIDEO_WIDTH, config.VIDEO_HEIGHT), Image.LANCZOS)
    draw = ImageDraw.Draw(img)

    w, h = img.size
    quote_len = len(quote)

    # ---- FONT SIZING: Big and bold for short quotes ----
    if quote_len < 60:
        font_size = 72
        wrap_width = 18
    elif quote_len < 100:
        font_size = 60
        wrap_width = 22
    elif quote_len < 150:
        font_size = 50
        wrap_width = 26
    else:
        font_size = 42
        wrap_width = 30

    # Load font
    try:
        font = ImageFont.truetype(config.FONT_PATH, size=font_size)
    except (IOError, OSError):
        try:
            font = ImageFont.truetype("arial.ttf", size=font_size)
        except (IOError, OSError):
            font = ImageFont.load_default()
            print("⚠️ Using default font.")

    # Wrap text
    wrapped = textwrap.fill(quote, width=wrap_width)

    # Calculate text position — centered in lower third
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = (w - text_w) / 2
    # Place in lower third: between 60% and 90% of image height
    y = h * 0.60 + (h * 0.30 - text_h) / 2
    y = max(h * 0.55, min(y, h - text_h - 60))

    # ---- DRAW TEXT WITH STRONG OUTLINE ----
    outline_width = 3
    outline_color = "black"

    # Draw outline (8 directions for thick outline effect)
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx == 0 and dy == 0:
                continue
            draw.multiline_text(
                (x + dx, y + dy), wrapped,
                font=font, fill=outline_color, align="center"
            )

    # Draw main white text on top
    draw.multiline_text(
        (x, y), wrapped, font=font, fill="white", align="center"
    )

    img.save(output_path, quality=95)
    print(f"🖼️ Quote image saved as {output_path}")
    return output_path
