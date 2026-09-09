"""
tests/test_gemini_image_gen.py — Test Google Imagen 3 image generation.
Tests image generation standalone and verifies image output dimensions.
"""
import os
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure root directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config
from services import image_gen
from PIL import Image


def test_imagen_generation():
    print("=" * 60)
    print("🧪 TESTING GOOGLE IMAGEN 3 IMAGE GENERATION")
    print(f"🔑 Gemini API Key configured: {'YES (starts with ' + config.GEMINI_API_KEY[:6] + '...)' if config.GEMINI_API_KEY else 'NO'}")
    print(f"🎯 Model: {config.IMAGEN_MODEL}")
    print(f"📐 Aspect Ratio: {config.IMAGEN_ASPECT_RATIO}")
    print("=" * 60)

    sample_quote = "Discipline is choosing between what you want now and what you want most."
    output_dir = os.path.join(os.path.dirname(__file__), "..", "images")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n🎨 Testing prompt generation for quote: \"{sample_quote}\"")
    image_path = image_gen.generate_image(
        output_dir=output_dir,
        quote=sample_quote,
        composition="portrait"
    )

    print(f"\n✅ Image generation returned path: {image_path}")
    assert os.path.exists(image_path), f"File {image_path} does not exist!"
    file_size = os.path.getsize(image_path)
    print(f"📦 File size: {file_size:,} bytes")
    assert file_size > 5000, f"File size too small ({file_size} bytes)!"

    # Verify image opens properly with PIL
    with Image.open(image_path) as img:
        w, h = img.size
        print(f"🖼️  Image dimensions: {w}x{h} (format: {img.format})")
        assert w > 0 and h > 0, "Invalid image dimensions!"

    print("\n🎉 TEST PASSED! Image successfully generated and verified.")
    return image_path


if __name__ == "__main__":
    try:
        path = test_imagen_generation()
        print(f"\nGenerated test image located at: {path}")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
