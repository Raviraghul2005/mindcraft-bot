"""
services/video.py — Create video with cinematic effects from a quote image + music.

Effects:
  - Fade in (0.8s) / Fade out (1.0s)
  - Slow Ken Burns zoom (1.0x → 1.10x over 20s)
  - Vignette overlay (dark edges)
  - Dynamic film grain (visible, textured)
  - Camera shake/jitter (subtle random movement for energy)
  - Flash pulse at text reveal (~2s mark)
  - Brief glitch/RGB split effect (~1.5s and ~12s)
  - Audio fade in (1.0s) / fade out (2.0s)
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


def _apply_ken_burns(frame, t, duration, zoom_factor=1.10):
    """Apply slow zoom with subtle breathing pulse."""
    h, w = frame.shape[:2]
    # Base zoom: linear 1.0 → zoom_factor
    progress = t / duration
    base_scale = 1.0 + (zoom_factor - 1.0) * progress
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


def _get_flash_intensity(t):
    """Return flash brightness multiplier at time t.
    Brief white flash at ~2.0s (text reveal moment) and subtle pulse at ~10s."""
    flash = 0.0
    # Main flash at text reveal (t=2.0s), duration ~0.3s
    if 1.8 <= t <= 2.3:
        # Quick triangle flash
        if t <= 2.0:
            flash = (t - 1.8) / 0.2 * 0.25
        else:
            flash = max(0, (2.3 - t) / 0.3 * 0.25)
    # Subtle pulse at midpoint
    elif 9.5 <= t <= 10.0:
        flash = (1 - abs(t - 9.75) / 0.25) * 0.08
    return flash


def _get_glitch_intensity(t):
    """Return glitch intensity at time t. Brief glitches at specific moments."""
    # Quick glitch at ~1.5s (before text reveal)
    if 1.3 <= t <= 1.6:
        return 0.5 * (1 - abs(t - 1.45) / 0.15)
    # Another at ~12s for variety
    if 11.8 <= t <= 12.1:
        return 0.4 * (1 - abs(t - 11.95) / 0.15)
    return 0.0


def create_video(quote_image_path, music_track_path, output_path=None):
    """
    Create a 20-second video with engaging effects.
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

    # --- Build the main clip with all effects ---
    def make_frame(t):
        # 1. Ken Burns zoom with breathing
        frame = _apply_ken_burns(base_frame, t, duration, zoom_factor=1.10)

        # 2. Camera shake (subtle jitter)
        frame = _apply_camera_shake(frame, t)

        # 3. Apply vignette
        vig_alpha = vignette[:, :, 3:4].astype(np.float32) / 255.0
        frame = frame.astype(np.float32)
        frame = frame * (1 - vig_alpha)

        # 4. Film grain (dynamic, visible)
        grain = np.random.normal(0, 12, frame.shape).astype(np.float32)
        frame = frame + grain

        # 5. Flash pulse
        flash = _get_flash_intensity(t)
        if flash > 0:
            frame = frame + flash * 255

        # 6. Glitch effect
        glitch = _get_glitch_intensity(t)
        if glitch > 0:
            frame = np.clip(frame, 0, 255).astype(np.uint8)
            frame = _apply_glitch(frame, glitch).astype(np.float32)

        return np.clip(frame, 0, 255).astype(np.uint8)

    main_clip = VideoClip(make_frame, duration=duration).set_fps(config.VIDEO_FPS)

    # --- Apply fade in/out ---
    main_clip = main_clip.fadein(0.8).fadeout(1.0)

    # --- Load and prepare audio ---
    audio = AudioFileClip(music_track_path)

    # Loop if audio is too short
    if audio.duration < duration:
        from moviepy.editor import concatenate_audioclips
        loops_needed = int(duration / audio.duration) + 1
        audio = concatenate_audioclips([audio] * loops_needed)

    audio = audio.subclip(0, duration)
    audio = audio.audio_fadein(1.0).audio_fadeout(2.0)

    # --- Combine ---
    final = main_clip.set_audio(audio)

    # --- Write output ---
    print(f"🎬 Creating video: {output_path} ({duration}s, {w}x{h}, {config.VIDEO_FPS}fps)")
    print(f"   Effects: Ken Burns zoom, camera shake, grain, vignette, flash pulse, glitch")
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
