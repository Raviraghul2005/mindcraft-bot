"""
services/video.py — Create video with cinematic effects from a quote image + music.

Effects:
  - Fade in (0.12s, kept short so it doesn't wash out the opening flash) / Fade out (0.3s, loop-friendly)
  - Slow Ken Burns zoom (pre-zoomed ~1.03x → ~1.12x over the clip)
  - Vignette overlay (dark edges)
  - Dynamic film grain (visible, textured)
  - Camera shake/jitter (subtle random movement for energy)
  - Flash pulse right at the open (hook, before a viewer can swipe) + subtle midpoint pulse
  - Brief glitch/RGB split effect paired with the opening flash + one near the end
  - Quote text fades/slides in over the open (see services/image_overlay.py for the layer)
  - Follow CTA fades in during the last ~1.2s
  - Audio fade in (0.3s) / fade out (0.6s)
"""
import os
import glob
import json
import numpy as np
from PIL import Image
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip,
    VideoClip, concatenate_videoclips
)
import config


import random

# Path to the music history tracking file (project root)
MUSIC_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "music_history.json")


def _load_music_history():
    """Load the list of recently used track filenames from disk."""
    if os.path.exists(MUSIC_HISTORY_FILE):
        try:
            with open(MUSIC_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("used_tracks", [])
        except (json.JSONDecodeError, IOError):
            return []
    return []


def _save_music_history(used_tracks):
    """Save the list of used track filenames to disk."""
    with open(MUSIC_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump({"used_tracks": used_tracks}, f, indent=2, ensure_ascii=False)


def get_music_track(row_index, sheets_client=None):
    """Select a music track using round-robin rotation.
    
    Picks randomly from tracks that haven't been used yet.
    Once all tracks have been played, resets and starts over.
    This ensures every track gets used before any repeats.
    
    Uses Google Sheets for persistence (works on GitHub Actions).
    Falls back to local JSON if Sheets is unavailable.
    """
    music_dir = config.MUSIC_DIR
    tracks = sorted(glob.glob(os.path.join(music_dir, "*")))
    tracks = [t for t in tracks if t.lower().endswith(('.mp3', '.wav', '.mpeg', '.ogg', '.m4a'))]

    if not tracks:
        raise FileNotFoundError(f"❌ No music files found in {music_dir}")

    # Get all track filenames (basenames for comparison)
    all_filenames = [os.path.basename(t) for t in tracks]

    # Try Google Sheets first (persists across CI runs), fall back to local JSON
    use_sheets = False
    if sheets_client:
        try:
            from services import sheets as sheets_svc
            used_tracks = sheets_svc.get_music_history(sheets_client)
            use_sheets = True
        except Exception as e:
            print(f"⚠️ Sheets music history unavailable ({e}), using local JSON fallback.")
            used_tracks = _load_music_history()
    else:
        used_tracks = _load_music_history()

    # Filter to only unused tracks
    unused_filenames = [f for f in all_filenames if f not in used_tracks]

    # If all tracks have been used, reset the history
    if not unused_filenames:
        print(f"🔄 All {len(all_filenames)} tracks played! Resetting rotation...")
        if use_sheets:
            from services import sheets as sheets_svc
            sheets_svc.reset_music_history(sheets_client)
        else:
            _save_music_history([])
        used_tracks = []
        unused_filenames = all_filenames.copy()

    # Pick a random track from the unused pool
    chosen_filename = random.choice(unused_filenames)

    # Find the full path for the chosen track
    track = next(t for t in tracks if os.path.basename(t) == chosen_filename)

    # Update history and save
    if use_sheets:
        from services import sheets as sheets_svc
        sheets_svc.add_to_music_history(sheets_client, chosen_filename)
    else:
        used_tracks.append(chosen_filename)
        _save_music_history(used_tracks)

    remaining = len(unused_filenames) - 1
    storage = "Sheets" if use_sheets else "local"
    print(f"🎵 Selected track: {chosen_filename} ({remaining} unused tracks remaining) [{storage}]")
    return track


def _create_vignette(width, height):
    """Create a vignette overlay — dark gradient at edges."""
    Y, X = np.ogrid[:height, :width]
    cx, cy = width / 2, height / 2
    dist = np.sqrt((X - cx) ** 2 / (cx ** 2) + (Y - cy) ** 2 / (cy ** 2))
    vignette = np.clip((dist - 0.5) * 1.6, 0, 1)
    vig_array = np.zeros((height, width, 4), dtype=np.uint8)
    vig_array[:, :, 3] = (vignette * 200).astype(np.uint8)
    return vig_array


def _apply_ken_burns(frame, t, duration, start_scale=1.03, end_scale=1.12):
    """Apply slow zoom with subtle breathing pulse.

    Starts already slightly zoomed in (instead of exactly 1.0x) so the very
    first frame reads as "landed on a shot" rather than a flat static image —
    part of making the opening more of a scroll-stopping hook.
    """
    h, w = frame.shape[:2]
    # Base zoom: linear start_scale → end_scale
    progress = t / duration
    base_scale = start_scale + (end_scale - start_scale) * progress
    # Add subtle breathing pulse (sine wave)
    breath = np.sin(t * 1.2) * 0.008  # very subtle oscillation
    scale = base_scale + breath

    new_w = int(w * scale)
    new_h = int(h * scale)

    img = Image.fromarray(frame)
    img_resized = img.resize((new_w, new_h), Image.LANCZOS)

    left = (new_w - w) // 2
    top = (new_h - h) // 2
    img_cropped = img_resized.crop((left, top, left + w, top + h))

    return np.array(img_cropped)


def _apply_camera_shake(frame, t):
    """Apply very subtle camera shake — minimal random pixel offset."""
    h, w = frame.shape[:2]
    rng = np.random.RandomState(int(t * 1000) % 2**31)
    # Minimal shake: just 1 pixel max
    shake_x = rng.randint(-1, 2)
    shake_y = rng.randint(-1, 2)

    frame = np.roll(frame, shake_x, axis=1)
    frame = np.roll(frame, shake_y, axis=0)
    return frame


def _apply_glitch(frame, intensity=0.3):
    """Apply a brief RGB channel split / glitch effect."""
    h, w = frame.shape[:2]
    result = frame.copy()
    offset = max(1, min(int(8 * intensity), w // 4))

    # Shift red channel right
    result[:, offset:, 0] = frame[:, :w - offset, 0]
    # Shift blue channel left
    result[:, :w - offset, 2] = frame[:, offset:, 2]

    # Add a horizontal scan line glitch
    scan_line = min(np.random.randint(0, h), h - 4)
    band_h = max(2, min(int(6 * intensity), h - scan_line - 1))
    shift = max(1, int(15 * intensity))
    result[scan_line:scan_line + band_h, :] = np.roll(
        result[scan_line:scan_line + band_h, :], shift, axis=1
    )
    return result


def _triangle_pulse(t, center, half_width, peak):
    """A triangular pulse: 0 outside [center-half_width, center+half_width], peaking at `peak`."""
    dist = abs(t - center)
    if dist >= half_width:
        return 0.0
    return peak * (1 - dist / half_width)


def _get_flash_intensity(t, duration):
    """Return flash brightness multiplier at time t.

    The main flash sits right at the open (absolute timing, not scaled to
    duration — the swipe-away decision happens in the first ~1-2s regardless
    of how long the video is) so there's a scroll-stopping visual event
    before a viewer decides to swipe, instead of ~2s in. A subtle secondary
    pulse near the midpoint adds texture.
    """
    return max(
        _triangle_pulse(t, center=0.1, half_width=0.15, peak=0.30),
        _triangle_pulse(t, center=duration * 0.5, half_width=0.25, peak=0.08),
    )


def _get_glitch_intensity(t, duration):
    """Return glitch intensity at time t.

    Paired with the opening flash (sells a "cut landed here" feel), plus
    one more glitch near the end for texture.
    """
    return max(
        _triangle_pulse(t, center=0.15, half_width=0.15, peak=0.5),
        _triangle_pulse(t, center=duration * 0.85, half_width=0.15, peak=0.4),
    )


def _ease_smoothstep(p):
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


def _get_text_reveal(t, window=0.35):
    """Fade/slide-in progress (0-1) for the quote text, landing together with
    the opening flash/glitch instead of being static from frame 0."""
    return _ease_smoothstep(t / window)


def _get_cta_reveal(t, duration, window=1.2, fade=0.3):
    """Fade-in progress (0-1) for the follow CTA, appearing only in the
    last `window` seconds — after a viewer has already stuck around."""
    start = max(0.0, duration - window)
    if t < start:
        return 0.0
    return _ease_smoothstep((t - start) / fade)


def _shift_vertical(rgba_array, offset_px):
    """Shift an RGBA array down by offset_px (float, rounded), filling the
    gap with transparent/zero rows. Used for the text slide-in."""
    offset_px = int(round(offset_px))
    if offset_px == 0:
        return rgba_array
    h = rgba_array.shape[0]
    shifted = np.zeros_like(rgba_array)
    if offset_px > 0:
        shifted[offset_px:, :, :] = rgba_array[:h - offset_px, :, :]
    else:
        o = -offset_px
        shifted[:h - o, :, :] = rgba_array[o:, :, :]
    return shifted


def _composite_layer(frame, layer_rgb, layer_alpha):
    """Alpha-composite an RGB layer (float32, 0-255) with per-pixel alpha
    (float32, 0-1, shape (h, w, 1)) onto `frame` (float32, 0-255)."""
    return frame * (1 - layer_alpha) + layer_rgb * layer_alpha


def create_video(quote_image_path, text_layer, cta_layer, music_track_path, output_path=None):
    """
    Create a short video (config.VIDEO_DURATION seconds) with engaging effects.

    `text_layer` and `cta_layer` are transparent RGBA PIL Images (see
    services/image_overlay.py) composited on top of the fully-processed
    background each frame, with their own fade/slide-in animation — this is
    what makes the quote text "land" as part of the opening hook instead of
    being static from frame 0.

    Returns the output video file path.
    """
    if output_path is None:
        output_path = config.VIDEO_OUTPUT_FILE

    duration = config.VIDEO_DURATION
    w, h = config.VIDEO_WIDTH, config.VIDEO_HEIGHT

    # --- Load the quote image ---
    img = Image.open(quote_image_path).convert("RGB")
    img = img.resize((w, h), Image.LANCZOS)
    base_frame = np.array(img)

    # --- Create vignette overlay ---
    vignette = _create_vignette(w, h)

    # --- Precompute text/CTA layers as float32 RGB + alpha arrays ---
    text_rgba = np.array(text_layer.convert("RGBA")).astype(np.float32)
    text_rgb, text_alpha = text_rgba[:, :, :3], text_rgba[:, :, 3:4] / 255.0

    cta_rgba = np.array(cta_layer.convert("RGBA")).astype(np.float32)
    cta_rgb, cta_alpha = cta_rgba[:, :, :3], cta_rgba[:, :, 3:4] / 255.0

    # --- Build the main clip with all effects ---
    def make_frame(t):
        # 1. Ken Burns zoom with breathing (starts slightly pre-zoomed — see _apply_ken_burns)
        frame = _apply_ken_burns(base_frame, t, duration)

        # 2. Camera shake (subtle jitter)
        frame = _apply_camera_shake(frame, t)

        # 3. Apply vignette
        vig_alpha = vignette[:, :, 3:4].astype(np.float32) / 255.0
        frame = frame.astype(np.float32)
        frame = frame * (1 - vig_alpha)

        # 4. Film grain (dynamic, visible)
        grain = np.random.normal(0, 12, frame.shape).astype(np.float32)
        frame = frame + grain

        # 5. Flash pulse (opening punch-in + subtle midpoint pulse)
        flash = _get_flash_intensity(t, duration)
        if flash > 0:
            frame = frame + flash * 255

        # 6. Glitch effect (paired with the opening flash + one near the end)
        glitch = _get_glitch_intensity(t, duration)
        if glitch > 0:
            frame = np.clip(frame, 0, 255).astype(np.uint8)
            frame = _apply_glitch(frame, glitch).astype(np.float32)

        # 7. Quote text — fades/slides in over the open, landing with the hook.
        #    Composited after grain/glitch so the text itself stays crisp/legible.
        reveal = _get_text_reveal(t)
        if reveal > 0:
            slide = (1 - reveal) * 24  # px, settles to 0 as reveal completes
            layer_rgb = _shift_vertical(text_rgb, slide) if slide else text_rgb
            layer_alpha = _shift_vertical(text_alpha, slide) if slide else text_alpha
            frame = _composite_layer(frame, layer_rgb, layer_alpha * reveal)

        # 8. Follow CTA — fades in only in the last stretch, once someone has stuck around.
        cta_reveal = _get_cta_reveal(t, duration)
        if cta_reveal > 0:
            frame = _composite_layer(frame, cta_rgb, cta_alpha * cta_reveal)

        return np.clip(frame, 0, 255).astype(np.uint8)

    main_clip = VideoClip(make_frame, duration=duration).set_fps(config.VIDEO_FPS)

    # --- Apply fade in/out ---
    # Fade-in is kept very short so it doesn't wash out the opening flash/glitch
    # hook. Fade-out is short and symmetric-ish so a loop replay feels tight.
    main_clip = main_clip.fadein(0.12).fadeout(0.3)

    # --- Load and prepare audio ---
    audio = AudioFileClip(music_track_path)

    # Loop if audio is too short
    if audio.duration < duration:
        from moviepy.editor import concatenate_audioclips
        loops_needed = int(duration / audio.duration) + 1
        audio = concatenate_audioclips([audio] * loops_needed)

    audio = audio.subclip(0, duration)
    audio = audio.audio_fadein(0.3).audio_fadeout(0.6)

    # --- Combine ---
    final = main_clip.set_audio(audio)

    # --- Write output ---
    print(f"🎬 Creating video: {output_path} ({duration}s, {w}x{h}, {config.VIDEO_FPS}fps)")
    print(f"   Effects: Ken Burns zoom, camera shake, grain, vignette, flash pulse, glitch, text reveal, CTA")
    final.write_videofile(
        output_path,
        fps=config.VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=2,
        logger=None
    )

    # Cleanup
    audio.close()
    main_clip.close()
    final.close()

    print(f"✅ Video created: {output_path}")
    return output_path
