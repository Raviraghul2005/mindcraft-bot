"""
config.py — Loads environment variables and defines constants.
Works both locally (.env file) and on GitHub Actions (env secrets).
"""
import os
import json
import tempfile
from dotenv import load_dotenv

load_dotenv()

# ---- GEMINI & IMAGEN ----
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
IMAGEN_MODEL = "imagen-3.0-generate-002"
IMAGEN_ASPECT_RATIO = "3:4"  # 3:4 aspect ratio closely matches 1080x1350 (4:5)
GEMINI_IMAGE_MODEL = "imagen-3.0-generate-002"
GEMINI_IMAGE_MODEL_FALLBACK = "models/gemini-2.0-flash-exp-image-generation"
GEMINI_TEXT_MODEL = "models/gemini-2.5-flash"

# ---- POLLINATIONS AI (Fallback Image Generation) ----
USE_POLLINATIONS_IMAGE = False
POLLINATIONS_MODEL = "flux"

# ---- OPENROUTER (fallback for text) ----
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ---- GOOGLE SERVICE ACCOUNT ----
# On GitHub Actions, credentials come as a JSON string in the env var.
# Locally, they come from a file path.
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
_gcloud_json = os.getenv("GOOGLE_CREDENTIALS_JSON", "")

def get_google_credentials_path():
    """Return path to Google credentials file.
    If GOOGLE_CREDENTIALS_JSON env var is set (GitHub Actions),
    write it to a temp file and return that path.
    Otherwise, return the local file path.
    """
    if _gcloud_json:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.write(_gcloud_json)
        tmp.close()
        return tmp.name
    return GOOGLE_CREDENTIALS_PATH

# ---- INSTAGRAM ----
IG_USER_ID = os.getenv("IG_USER_ID", "")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")

# ---- YOUTUBE ----
YT_CLIENT_ID = os.getenv("YT_CLIENT_ID", "")
YT_CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET", "")
YT_REFRESH_TOKEN = os.getenv("YT_REFRESH_TOKEN", "")

# ---- GOOGLE SHEETS ----
SHEET_NAME = "Quote_Access"

# ---- QUOTE STYLE ----
# Fraction of each auto-replenished batch generated in the vivid (war/fire/nature
# metaphor) style vs. the calm/plainspoken style. Tune this once Phase 3 analytics
# (Style column in the sheet vs. YouTube Studio retention) confirm which wins.
QUOTE_STYLE_VIVID_RATIO = 0.7

# ---- IMAGE GENERATION PROMPT ----
IMAGE_PROMPT = (
    "Berserk manga art style, Kentaro Miura, dark fantasy, "
    "painterly ink illustration, extreme close-up face, "
    "dramatic chiaroscuro lighting, battle-scarred warrior, "
    "deep black background, rough brushstroke texture, "
    "gritty semi-realistic anime, warm ochre skin tones, "
    "heavy shadows, intense brooding expression"
)

# ---- VIDEO SETTINGS ----
VIDEO_DURATION = 9  # seconds — shorter clears the ~65% Shorts retention threshold more easily and loops faster
VIDEO_FPS = 24
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1350  # 4:5 aspect ratio for Instagram Reels

# ---- MUSIC ----
MUSIC_DIR = os.path.join(os.path.dirname(__file__), "Music")

# ---- OUTPUT ----
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "images")
QUOTE_IMAGE_FILE = "quote_image.jpg"
VIDEO_OUTPUT_FILE = "quote_video_with_audio.mp4"

# ---- INSTAGRAM CAPTION ----
INSTAGRAM_HANDLE = "@itsboldfist"
HASHTAGS = (
    "#motivation #stoic #darkfantasy #berserk #mindset "
    "#grindset #disciplineovermotivation #successmindset "
    "#neverquit #hustlehard #mentaltoughness #selfimprovement "
    "#motivationalquotes #dailymotivation #warrior #strength "
    "#nevergiveup #inspirational #mindcraft #riseandgrind"
)

# ---- FONT ----
FONT_PATH = os.path.join(os.path.dirname(__file__), "resources", "Roboto_Condensed-Bold.ttf")

# ---- SCOPES ----
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def validate(dry_run=False):
    """Validate that required config values are present."""
    missing = []
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not dry_run:
        cred_path = get_google_credentials_path()
        if not os.path.exists(cred_path):
            missing.append(f"Google credentials file ({cred_path})")
    if missing:
        raise EnvironmentError(f"❌ Missing config: {', '.join(missing)}")
    return True
