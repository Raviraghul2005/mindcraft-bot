"""
services/image_gen.py — Generate images relevant to the quote via Gemini API.
The image matches the quote's theme (not always a face).
"""
import os
import uuid
import base64
import requests
import config


COMPOSITIONS = ("portrait", "wide_scene", "symbol")

# Alternating these across videos keeps 500+ near-identical face portraits
# from blurring together in the feed — see image_gen.pick_composition().
_COMPOSITION_HINTS = {
    "portrait": (
        "Composition: an extreme close-up or bust-shot portrait of a single "
        "battle-worn figure, dramatic emotion in the eyes and posture."
    ),
    "wide_scene": (
        "Composition: a wide atmospheric landscape or environment shot — "
        "mountains, a storm-lit horizon, a ruined battlefield, or a lone "
        "figure small against a vast dark sky. NO close-up face."
    ),
    "symbol": (
        "Composition: a single symbolic object rendered large and dramatic "
        "in negative space — a blade, a lantern, a broken chain, a compass, "
        "an ember, a raven — with NO human figure."
    ),
}


def pick_composition(seed):
    """Deterministically rotate through COMPOSITIONS based on `seed`
    (e.g. the sheet row index) so consecutive videos vary visually."""
    return COMPOSITIONS[seed % len(COMPOSITIONS)]


def _build_prompt(quote, composition="portrait"):
    """
    Build an image prompt that matches the quote's theme.
    Combines the quote's meaning with the Berserk manga art style.
    """
    composition_hint = _COMPOSITION_HINTS.get(composition, _COMPOSITION_HINTS["portrait"])
    prompt = (
        f"Create a powerful, cinematic image that visually represents this concept: \"{quote}\"\n\n"
        "Art style requirements:\n"
        "- Berserk manga art style, dark fantasy, Kentaro Miura inspired\n"
        "- Painterly ink illustration with rough brushstroke texture\n"
        "- Dramatic chiaroscuro lighting, deep black background\n"
        "- Gritty, semi-realistic anime aesthetic\n"
        "- Heavy shadows, warm ochre and muted tones\n"
        "- The scene should be atmospheric and cinematic\n"
        f"- {composition_hint}\n"
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


def generate_image(output_dir=None, quote=None, composition="portrait"):
    """
    Generate an image. Tries Google Imagen 3 (imagen-3.0-generate-002) first.
    Falls back to Gemini multimodal models, and finally to Pollinations AI.
    If a quote is provided, the image will be relevant to the quote's theme.
    `composition` (see COMPOSITIONS) varies the shot type for visual variety
    across videos — pick it with pick_composition(row_index).
    Returns the path to the saved image file.
    """
    if output_dir is None:
        output_dir = config.IMAGES_DIR
    os.makedirs(output_dir, exist_ok=True)

    # Build prompt based on quote or use default
    if quote:
        prompt = _build_prompt(quote, composition=composition)
        print(f"🖌️ Composition: {composition}")
    else:
        prompt = config.IMAGE_PROMPT

    filename = os.path.join(output_dir, f"{uuid.uuid4()}.png")

    # 1. Primary: Google Imagen 3
    if config.GEMINI_API_KEY and not getattr(config, "USE_POLLINATIONS_IMAGE", False):
        print(f"🎨 Generating image with Google Imagen 3 ({getattr(config, 'IMAGEN_MODEL', 'imagen-3.0-generate-002')})...")
        try:
            aspect_ratio = getattr(config, "IMAGEN_ASPECT_RATIO", "3:4")
            result = _call_imagen_3(prompt, aspect_ratio=aspect_ratio)
            if result:
                with open(filename, "wb") as f:
                    f.write(result)
                _remove_white_borders(filename)
                print(f"📥 Image saved as {filename}")
                return filename
        except Exception as e:
            print(f"⚠️ Google Imagen 3 failed: {e}")

    # 2. Secondary fallback: Gemini multimodal image generation models
    if config.GEMINI_API_KEY:
        fallback_models = [
            getattr(config, "GEMINI_IMAGE_MODEL_FALLBACK", "models/gemini-2.0-flash-exp-image-generation")
        ]
        for model in fallback_models:
            if not model:
                continue
            print(f"🎨 Generating image fallback with Gemini ({model})...")
            try:
                result = _call_gemini_image(model, prompt)
                if result:
                    with open(filename, "wb") as f:
                        f.write(result)
                    _remove_white_borders(filename)
                    print(f"📥 Image saved as {filename}")
                    return filename
            except Exception as e:
                print(f"⚠️ {model} failed: {e}")

    # 3. Tertiary fallback: Pollinations AI (Flux)
    print(f"🎨 Falling back to Pollinations AI ({config.POLLINATIONS_MODEL})...")
    try:
        result = _call_pollinations_image(prompt)
        if result:
            with open(filename, "wb") as f:
                f.write(result)
            _remove_white_borders(filename)
            print(f"📥 Image saved as {filename}")
            return filename
    except Exception as e:
        print(f"⚠️ Pollinations AI fallback failed: {e}")

    raise RuntimeError("❌ All image generation models failed.")


def _call_imagen_3(prompt, aspect_ratio="3:4"):
    """
    Call Google Imagen 3 (imagen-3.0-generate-002) to generate a high quality image.
    Tries google-genai SDK first, falls back to direct REST API.
    """
    model = getattr(config, "IMAGEN_MODEL", "imagen-3.0-generate-002")
    api_key = config.GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    # 1. Try google-genai SDK
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        print(f"✨ Calling Imagen 3 via google-genai SDK ({model})...")
        response = client.models.generate_images(
            model=model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                output_mime_type="image/jpeg",
            ),
        )
        if response.generated_images:
            return response.generated_images[0].image.image_bytes
    except ImportError:
        pass
    except Exception as e:
        print(f"⚠️ Imagen 3 SDK call failed: {e}. Trying REST API endpoint...")

    # 2. Direct REST API call
    return _call_imagen_rest(prompt, aspect_ratio=aspect_ratio)


def _call_imagen_rest(prompt, aspect_ratio="3:4"):
    """
    Direct REST API call to generativelanguage.googleapis.com for Imagen 3 predict.
    """
    model = getattr(config, "IMAGEN_MODEL", "imagen-3.0-generate-002")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={config.GEMINI_API_KEY}"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            "outputOptions": {
                "mimeType": "image/jpeg"
            }
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": config.GEMINI_API_KEY,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=120)
    data = resp.json()

    if "error" in data:
        raise Exception(data["error"].get("message", str(data["error"])))

    if "predictions" in data and data["predictions"]:
        b64_data = data["predictions"][0].get("bytesBase64Encoded")
        if b64_data:
            return base64.b64decode(b64_data)

    raise Exception(f"No image data in Imagen 3 response: {str(data)[:200]}")


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
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
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
