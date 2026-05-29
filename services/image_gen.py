"""
services/image_gen.py — Generate images relevant to the quote via Gemini API.
The image matches the quote's theme (not always a face).
"""
import os
import uuid
import base64
import requests
import config


def _build_prompt(quote):
    """
    Build an image prompt that matches the quote's theme.
    Combines the quote's meaning with the Berserk manga art style.
    """
    prompt = (
        f"Create a powerful, cinematic image that visually represents this concept: \"{quote}\"\n\n"
        "Art style requirements:\n"
        "- Berserk manga art style, dark fantasy, Kentaro Miura inspired\n"
        "- Painterly ink illustration with rough brushstroke texture\n"
        "- Dramatic chiaroscuro lighting, deep black background\n"
        "- Gritty, semi-realistic anime aesthetic\n"
        "- Heavy shadows, warm ochre and muted tones\n"
        "- The scene should be atmospheric and cinematic\n"
        "- Can be a warrior, a landscape, an animal, a storm, fire, "
        "a sword, a silhouette — whatever matches the quote's meaning\n"
        "- NO TEXT in the image. Pure visual art only.\n"
        "- CRITICAL: The artwork MUST fill the ENTIRE canvas edge-to-edge. "
        "NO white borders, NO white margins, NO white background, NO empty white space anywhere. "
        "The background must be deep black or dark colors, never white.\n"
        "- Aspect ratio: portrait (taller than wide)"
    )
    return prompt


def _remove_white_borders(image_path):
    """
    Post-process: replace white/near-white border pixels with black.
    Scans from edges inward and replaces any bright border regions.
    """
    from PIL import Image as PILImage
    import numpy as np

    img = PILImage.open(image_path).convert("RGB")
    arr = np.array(img)

    # Threshold: pixels where ALL channels > 230 are considered "white"
    threshold = 230
    white_mask = np.all(arr > threshold, axis=2)

    # Replace white pixels with black
    arr[white_mask] = [0, 0, 0]

    result = PILImage.fromarray(arr)
    result.save(image_path)


def generate_image(output_dir=None, quote=None):
    """
    Generate an image. Try Pollinations AI first (if enabled), then fall back to Gemini API.
    If a quote is provided, the image will be relevant to the quote's theme.
    Returns the path to the saved image file.
    """
    if output_dir is None:
        output_dir = config.IMAGES_DIR
    os.makedirs(output_dir, exist_ok=True)

    # Build prompt based on quote or use default
    if quote:
        prompt = _build_prompt(quote)
    else:
        prompt = config.IMAGE_PROMPT

    filename = os.path.join(output_dir, f"{uuid.uuid4()}.png")

    # Try Pollinations AI first if enabled
    if getattr(config, "USE_POLLINATIONS_IMAGE", False):
        print(f"🎨 Generating image with Pollinations AI ({config.POLLINATIONS_MODEL})...")
        try:
            result = _call_pollinations_image(prompt)
            if result:
                with open(filename, "wb") as f:
                    f.write(result)
                # Post-process: remove any white borders
                _remove_white_borders(filename)
                print(f"📥 Image saved as {filename}")
                return filename
        except Exception as e:
            print(f"⚠️ Pollinations AI failed: {e}")

    # Fallback to Gemini image models
    models = [config.GEMINI_IMAGE_MODEL, config.GEMINI_IMAGE_MODEL_FALLBACK]

    for model in models:
        print(f"🎨 Generating image fallback with {model}...")
        try:
            result = _call_gemini_image(model, prompt)
            if result:
                with open(filename, "wb") as f:
                    f.write(result)
                # Post-process: remove any white borders
                _remove_white_borders(filename)
                print(f"📥 Image saved as {filename}")
                return filename
        except Exception as e:
            print(f"⚠️ {model} failed: {e}")
            continue

    raise RuntimeError("❌ All image generation models failed.")


def _call_pollinations_image(prompt):
    """
    Call Pollinations AI free API to generate an image.
    Returns raw image bytes or raises an Exception.
    """
    import urllib.parse
    import random
    encoded_prompt = urllib.parse.quote(prompt)
    model = getattr(config, "POLLINATIONS_MODEL", "flux")
    seed = random.randint(1, 99999999)
    # Fetch 1080x1350, matching standard config
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1350&model={model}&seed={seed}&nologo=true&private=true"
    
    print(f"🌐 Calling Pollinations API: {url.split('?')[0]}?...")
    resp = requests.get(url, timeout=120)
    
    if resp.status_code == 200:
        return resp.content
    else:
        raise Exception(f"Pollinations API returned status code {resp.status_code}: {resp.text[:200]}")


def _call_gemini_image(model, prompt):
    """
    Call Gemini API to generate an image.
    Returns raw image bytes or None.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={config.GEMINI_API_KEY}"

    resp = requests.post(url, json={
        "contents": [{"parts": [{"text": f"Generate an image: {prompt}"}]}],
        "generationConfig": {"responseModalalities": ["IMAGE", "TEXT"]},
    }, timeout=120)

    data = resp.json()

    if "error" in data:
        raise Exception(data["error"].get("message", str(data["error"])))

    if "candidates" not in data:
        raise Exception(f"No candidates in response: {str(data)[:200]}")

    parts = data["candidates"][0].get("content", {}).get("parts", [])

    for part in parts:
        if "inlineData" in part:
            b64_data = part["inlineData"]["data"]
            return base64.b64decode(b64_data)

    raise Exception("No image data found in Gemini response.")
