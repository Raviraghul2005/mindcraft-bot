"""
services/image_overlay.py — Build quote text (and follow-CTA) as transparent
RGBA layers for animated compositing in video.py, instead of baking text
permanently into the background image. This lets the video hook animate the
text in (fade + slide) rather than it being static from frame 0.
"""
import textwrap
from PIL import Image, ImageDraw, ImageFont
import config


_FONT_CANDIDATES = [
    config.FONT_PATH,
    # Linux (GitHub Actions, Ubuntu)
    "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Bold.ttf",
    "/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    # Windows
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _load_font(size):
    for candidate in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size=size)
        except (IOError, OSError):
            continue
    print(f"⚠️ No TTF font found — text will be tiny! Font size: {size}")
    return ImageFont.load_default()


def _draw_outlined_text(draw, xy, text, font, outline_width=3, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), multiline=True, align="center"):
    x, y = xy
    text_fn = draw.multiline_text if multiline else draw.text
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx == 0 and dy == 0:
                continue
            kwargs = {"align": align} if multiline else {}
            text_fn((x + dx, y + dy), text, font=font, fill=outline, **kwargs)
    kwargs = {"align": align} if multiline else {}
    text_fn((x, y), text, font=font, fill=fill, **kwargs)


def build_text_layer(quote, width, height):
    """
    Render the quote text onto a transparent RGBA layer sized (width, height).
    - BIG bold font — designed for short 1-2 line quotes
    - White text with strong black outline for max readability
    - Text centered in lower third of the frame

    Returns a PIL RGBA Image. Callers composite this onto video frames
    themselves (see services/video.py) so the text can be animated in.
    """
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

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

    font = _load_font(font_size)
    wrapped = textwrap.fill(quote, width=wrap_width)

    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = (width - text_w) / 2
    # Place in lower third: between 60% and 90% of frame height
    y = height * 0.60 + (height * 0.30 - text_h) / 2
    y = max(height * 0.55, min(y, height - text_h - 60))

    _draw_outlined_text(draw, (x, y), wrapped, font, outline_width=3)

    return layer


def build_cta_layer(width, height, handle=None):
    """
    Render a small "Follow @handle" call-to-action onto a transparent RGBA
    layer. Placed near the top so it never collides with the quote text
    (lower third) or platform UI (bottom safe area). video.py fades this in
    only during the last ~1.2s of the clip.
    """
    handle = handle or config.INSTAGRAM_HANDLE
    text = f"Follow {handle}"

    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    font = _load_font(34)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = (width - text_w) / 2
    y = height * 0.06

    _draw_outlined_text(draw, (x, y), text, font, outline_width=2, multiline=False)

    return layer


def save_preview(image_path, text_layer, cta_layer, output_path=None, width=None, height=None):
    """
    Flatten background + text + CTA into a single static JPG for quick human
    inspection (debugging / dry-run only — the actual video pipeline animates
    these layers itself and never touches this file).
    """
    if output_path is None:
        output_path = config.QUOTE_IMAGE_FILE
    width = width or config.VIDEO_WIDTH
    height = height or config.VIDEO_HEIGHT

    img = Image.open(image_path).convert("RGB").resize((width, height), Image.LANCZOS).convert("RGBA")
    img = Image.alpha_composite(img, text_layer)
    img = Image.alpha_composite(img, cta_layer)
    img.convert("RGB").save(output_path, quality=95)

    print(f"🖼️ Preview image saved as {output_path}")
    return output_path
