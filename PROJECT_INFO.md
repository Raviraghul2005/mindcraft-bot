# 🧠 MIND CRAFT — Complete Project Breakdown

## 🔥 What Is MIND CRAFT?

**MIND CRAFT** is a fully automated content pipeline that generates and publishes **motivational short-form video content** (Instagram Reels + YouTube Shorts) — completely hands-free, 24/7, using AI and cloud automation.

It creates **dark, stoic, warrior-mentality motivational videos** in a **Berserk manga art style** (Kentaro Miura inspired). Every video features:
- An AI-generated quote (dark, raw, warrior tone)
- An AI-generated Berserk-style illustration matching the quote
- Cinematic video effects (Ken Burns zoom, glitch, film grain, camera shake, flash pulse, vignette)
- Background music (phonk/dark beats)
- Auto-published to **Instagram Reels** and **YouTube Shorts**

The brand handle is **@itsboldfist**.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        MIND CRAFT PIPELINE                          │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│  │ Google Sheets │───▶│  Quote Gen   │───▶│     Image Gen         │  │
│  │ (Quote Store) │    │  (Gemini AI) │    │  (Gemini AI + Pillow) │  │
│  └──────────────┘    └──────────────┘    └───────────┬───────────┘  │
│                                                      │              │
│                                          ┌───────────▼───────────┐  │
│                                          │   Image Overlay       │  │
│                                          │  (Quote Text on Art)  │  │
│                                          └───────────┬───────────┘  │
│                                                      │              │
│                                          ┌───────────▼───────────┐  │
│                                          │   Video Creator       │  │
│                                          │  (MoviePy + Effects)  │  │
│                                          └───────────┬───────────┘  │
│                                                      │              │
│                              ┌───────────────────────▼────────┐     │
│                              │      Google Drive Upload       │     │
│                              │  (Temp public URL for IG API)  │     │
│                              └──────┬─────────────────┬───────┘     │
│                                     │                 │             │
│                          ┌──────────▼──────┐  ┌───────▼──────────┐  │
│                          │  Instagram API  │  │   YouTube API    │  │
│                          │  (Reels Upload) │  │  (Shorts Upload) │  │
│                          └─────────────────┘  └──────────────────┘  │
│                                                                     │
│                          ┌──────────────────────────────────────┐   │
│                          │  Cleanup + Mark Complete in Sheets   │   │
│                          └──────────────────────────────────────┘   │
│                                                                     │
│  ⚡ Triggered by: GitHub Actions (cron schedule) or manual run      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Tech Stack

| Category | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.11 | Core pipeline logic |
| **AI — Image Generation** | Google Gemini API (`gemini-2.5-flash-image`) | Generates Berserk-style manga art from text prompts |
| **AI — Text/Quote Gen** | Google Gemini API (`gemini-2.5-flash`) | Generates short, punchy motivational quotes |
| **AI Fallback (Text)** | OpenRouter API | Fallback LLM for quote generation |
| **Image Processing** | Pillow (PIL) + NumPy | Text overlay on images, white border removal, font rendering |
| **Video Creation** | MoviePy (<2.0) + FFmpeg | Creates videos with cinematic effects + audio mixing |
| **Database/Storage** | Google Sheets (via gspread) | Stores quotes, tracks completion status |
| **Cloud Storage** | Google Drive API v3 | Temporary video hosting (public URL for Instagram API) |
| **Cloud Storage Fallback** | tmpfiles.org API | Free fallback temp file hosting (1-hour auto-delete) |
| **Social — Instagram** | Instagram Graph API / Facebook Graph API v21.0 | Publishes Reels with captions + hashtags |
| **Social — YouTube** | YouTube Data API v3 | Uploads Shorts via OAuth2 resumable upload |
| **Auth — Google Services** | Google Service Account (OAuth2) | Sheets + Drive access |
| **Auth — YouTube** | OAuth2 Refresh Token flow | YouTube upload (service accounts can't upload videos) |
| **CI/CD** | GitHub Actions | Automated scheduled runs (cron-based) |
| **Config Management** | python-dotenv + .env file | Local dev env vars; GitHub Secrets for production |
| **Font** | Roboto Condensed Bold (TTF) | Custom bold font for quote overlay |

---

## 📁 Project Structure

```
MIND CRAFT/
├── main.py                     # 🎯 Pipeline orchestrator — runs the full 8-step pipeline
├── config.py                   # ⚙️  Config loader — env vars, constants, model names, video settings
├── requirements.txt            # 📦 Python dependencies
├── credentials.json            # 🔐 Google Service Account credentials (gitignored)
├── .env                        # 🔐 API keys & secrets (gitignored)
├── .gitignore                  # Files excluded from git
├── yt_auth_setup.py            # 🔑 One-time YouTube OAuth2 token generator
├── DEPLOYMENT_GUIDE.md         # 📘 Deployment instructions
│
├── services/                   # 🧩 Modular service layer (8 modules)
│   ├── __init__.py
│   ├── quote_gen.py            # 💬 AI quote generation via Gemini
│   ├── image_gen.py            # 🎨 AI image generation via Gemini
│   ├── image_overlay.py        # ✍️  Text overlay on generated images
│   ├── video.py                # 🎬 Video creation with cinematic effects
│   ├── sheets.py               # 📋 Google Sheets read/write operations
│   ├── drive_upload.py         # ☁️  Google Drive upload + fallback
│   ├── instagram.py            # 📲 Instagram Reels publishing
│   └── youtube.py              # 📺 YouTube Shorts uploading
│
├── Music/                      # 🎵 Background music tracks (9 files)
│   ├── Various phonk/dark beats (.mp3, .m4a)
│   └── (round-robin rotation — every track plays before any repeats)
│
├── images/                     # 🖼️  Generated images (temp, gitignored)
├── resources/
│   └── Roboto_Condensed-Bold.ttf  # Custom font
│
├── reference images/           # Reference art for style guidance
│
└── .github/
    └── workflows/
        └── publish.yml         # 🤖 GitHub Actions CI/CD workflow
```

---

## 🔄 The Pipeline — Step by Step

The pipeline runs as a single `python main.py` execution. Here's every step:

### Step 0: Validate Config
- Checks that all required environment variables are set (Gemini API key, Google credentials, etc.)
- Supports a `--dry-run` flag that skips uploads and just generates content locally

### Step 1: Get Next Quote
- Connects to **Google Sheets** (sheet name: `Quote_Access`) using a **Service Account**
- Fetches the first row where `Status` column ≠ `Complete`
- If all rows are complete → **auto-generates 10 new quotes** via Gemini AI and appends them to the sheet
- Quote style: dark, stoic, warrior mentality — 1-2 sentences, under 80 words
- Uses metaphors from nature, war, fire, storms, lions, wolves, swords
- Fallback: 10 hardcoded quotes if API fails

### Step 2: Generate Image
- Builds a context-aware prompt combining the quote's meaning with the **Berserk manga art style**
- Calls **Gemini API** (`gemini-2.5-flash-image`) to generate an image
- Falls back to `gemini-2.0-flash-exp-image-generation` if primary model fails
- Post-processes: removes any white/near-white border pixels (replaces with black)
- Saves as UUID-named PNG in `images/` directory
- Art style: dark fantasy, Kentaro Miura inspired, painterly ink illustration, dramatic chiaroscuro lighting, deep black background, gritty semi-realistic anime

### Step 3: Overlay Quote Text
- Opens the generated image, resizes to **1080×1350** pixels (4:5 Instagram aspect ratio)
- Dynamically sizes font based on quote length:
  - <60 chars → 72px font, 18-char wrap
  - <100 chars → 60px font, 22-char wrap
  - <150 chars → 50px font, 26-char wrap
  - 150+ chars → 42px font, 30-char wrap
- Uses **Roboto Condensed Bold** font (with fallback to system fonts)
- Renders white text with a thick black outline (8-directional stroke, 3px)
- Positions text centered in the **lower third** of the image (60-90% height zone)

### Step 4: Create Video
- Creates a **15-second** video at **1080×1350** resolution, **24 FPS**
- Selects a music track using **round-robin rotation** from the `Music/` folder (9 phonk/dark beats available) — every track plays before any repeats, history tracked in Google Sheets (`Music_History` tab)
- Applies **6 cinematic effects**:
  1. **Ken Burns Zoom**: Slow 1.0x → 1.10x zoom with subtle sine-wave breathing pulse
  2. **Camera Shake**: Random 1px jitter for energy (seeded per-frame)
  3. **Vignette**: Dark gradient overlay at edges (radial falloff)
  4. **Film Grain**: Dynamic Gaussian noise (σ=12) — visible, textured
  5. **Flash Pulse**: Brief white flash at 2.0s (text reveal moment) + subtle pulse at 10s
  6. **Glitch/RGB Split**: Brief channel offset + scan line displacement at 1.5s and 12s
- **Audio**: Looped if shorter than 15s, with 1.0s fade-in and 2.0s fade-out
- **Video fades**: 0.8s fade-in, 1.0s fade-out
- Encoded with **libx264** codec, **AAC** audio

### Step 5: Upload to Google Drive
- Uploads the video to a `mindcraft_temp` folder in Google Drive
- Makes the file **publicly accessible** (anyone with link can view)
- Returns a **direct download URL** for Instagram's API to fetch
- **Fallback**: If Drive fails (e.g., quota exceeded), uploads to **tmpfiles.org** (free, 1-hour auto-delete)

### Step 6: Publish to Instagram Reels
- Uses the **Instagram Graph API** (or Facebook Graph API v21.0, auto-detected by token type)
- **3-step publish process**:
  1. **Create media container** — sends video URL, caption, `media_type=REELS`
  2. **Poll for processing** — checks container status every 5 seconds, max wait 120 seconds
  3. **Publish** — makes the reel live once container is `FINISHED`
- Caption format:
  ```
  "The quote text here"

  Follow @itsboldfist for daily motivation

  #motivation #stoic #darkfantasy #berserk #mindset #grindset ...
  ```
- Uses 20 curated hashtags

### Step 6b: Upload to YouTube Shorts
- Uses **YouTube Data API v3** with **OAuth2 refresh token** flow
- Refreshes access token using client_id + client_secret + refresh_token
- **Resumable upload** protocol:
  1. Initiate upload with metadata (title, description, tags, category)
  2. PUT the video binary data to the upload URL
- Metadata:
  - **Title**: First 90 chars of quote
  - **Description**: Full quote + hashtags + `#Shorts` tag
  - **Category**: 22 (People & Blogs)
  - **Privacy**: Public
  - **Tags**: Shorts, motivation, stoic, berserk, mindset, grindset, warrior, dark fantasy, quotes

### Step 7: Cleanup
- **Deletes** the video from Google Drive (Instagram has already processed it)
- Removes all local temp files (raw image, quote image, video)

### Step 8: Mark Complete
- Updates the Google Sheet row's `Status` column to `Complete`
- Only marks complete if **at least one platform** (Instagram or YouTube) succeeded
- Prevents re-processing the same quote on next run

---

## 🔌 APIs Used

### 1. Google Gemini API
- **Endpoint**: `https://generativelanguage.googleapis.com/v1beta/`
- **Models used**:
  - `models/gemini-2.5-flash-image` — Primary image generation
  - `models/gemini-2.0-flash-exp-image-generation` — Fallback image generation
  - `models/gemini-2.5-flash` — Text/quote generation
- **Auth**: API key (query parameter)
- **Used for**: Generating motivational quotes AND generating Berserk-style artwork

### 2. Google Sheets API
- **Library**: `gspread` (Python wrapper)
- **Auth**: Google Service Account (credentials.json)
- **Scopes**: `spreadsheets`, `drive`
- **Sheet name**: `Quote_Access`
- **Columns**: `Quote`, `Status` (Pending/Complete)
- **Used for**: Reading quotes, marking as complete, appending new AI-generated quotes

### 3. Google Drive API v3
- **Library**: `google-api-python-client`
- **Auth**: Google Service Account
- **Used for**: Uploading video to get a public URL (required by Instagram's API — it can't accept local files)
- **Folder**: `mindcraft_temp` (auto-created)
- **Cleanup**: Video is deleted after Instagram processes it

### 4. Instagram Graph API
- **Base URL**: `https://graph.instagram.com` (Instagram tokens) or `https://graph.facebook.com/v21.0` (Facebook tokens)
- **Auth**: Instagram/Facebook access token (long-lived, starts with `IGAA...`)
- **Token type auto-detection**: Checks if token starts with `IGAA` to determine Instagram vs Facebook API base
- **Flow**: Create container → Poll status → Publish
- **Media type**: REELS

### 5. YouTube Data API v3
- **Endpoint**: `https://www.googleapis.com/upload/youtube/v3/videos`
- **Auth**: OAuth2 (client_id + client_secret + refresh_token → access_token)
- **Upload type**: Resumable
- **Why OAuth2?**: YouTube doesn't allow service accounts to upload videos — requires user-level OAuth consent
- **One-time setup**: `yt_auth_setup.py` script handles the browser-based OAuth flow to get the initial refresh token

### 6. tmpfiles.org API (Fallback)
- **Endpoint**: `https://tmpfiles.org/api/v1/upload`
- **Auth**: None (free, public)
- **Used when**: Google Drive upload fails (quota, auth issues)
- **Limitation**: Files auto-delete after 1 hour

### 7. OpenRouter API (Fallback)
- **Purpose**: Alternative LLM provider for quote generation if Gemini fails
- **Currently**: Configured but Gemini is primary

---

## 🔐 Environment Variables & Secrets

| Variable | Service | Description |
|---|---|---|
| `GEMINI_API_KEY` | Gemini AI | API key for image + text generation |
| `OPENROUTER_API_KEY` | OpenRouter | Fallback LLM API key |
| `GOOGLE_CREDENTIALS_PATH` | Google Cloud | Path to service account JSON (local) |
| `GOOGLE_CREDENTIALS_JSON` | Google Cloud | Full JSON content as string (GitHub Actions) |
| `IG_USER_ID` | Instagram | Instagram Business account user ID |
| `IG_ACCESS_TOKEN` | Instagram | Long-lived Instagram/Facebook access token |
| `YT_CLIENT_ID` | YouTube | OAuth2 client ID |
| `YT_CLIENT_SECRET` | YouTube | OAuth2 client secret |
| `YT_REFRESH_TOKEN` | YouTube | OAuth2 refresh token (obtained via `yt_auth_setup.py`) |

---

## 🤖 CI/CD — GitHub Actions

The pipeline runs on **GitHub Actions** with a cron schedule:

- **Schedule**: Runs **twice daily**
  - 🌅 **9:00 AM IST** (3:30 AM UTC)
  - 🌙 **7:00 PM IST** (1:30 PM UTC)
- **Manual trigger**: Can also be triggered manually from the GitHub Actions UI (`workflow_dispatch`)
- **Runner**: `ubuntu-latest`
- **Timeout**: 10 minutes per run
- **Python version**: 3.11
- **System dependencies installed**: `ffmpeg`, `fonts-roboto`
- **All secrets are stored as GitHub repository secrets**

This means the entire pipeline — from quote generation to publishing on Instagram and YouTube — runs completely serverless and free, without any PC or server running.

---

## 📦 Python Dependencies

| Package | Version | Purpose |
|---|---|---|
| `python-dotenv` | Latest | Load .env file for local development |
| `gspread` | Latest | Google Sheets Python client |
| `google-auth` | Latest | Google authentication library |
| `google-auth-oauthlib` | Latest | OAuth2 for YouTube |
| `google-api-python-client` | Latest | Google Drive API client |
| `Pillow` | Latest | Image processing (overlay, resize, font rendering) |
| `moviepy` | <2.0 | Video creation, audio mixing, effects |
| `numpy` | Latest | Array operations for image effects (grain, vignette, glitch) |
| `requests` | Latest | HTTP requests to Gemini, Instagram, YouTube, tmpfiles APIs |

**System dependency**: `ffmpeg` (required by MoviePy for video encoding)

---

## 🎨 Content Style & Branding

- **Visual Style**: Berserk manga art (Kentaro Miura), dark fantasy, painterly ink illustration
- **Color Palette**: Deep blacks, warm ochre skin tones, muted dark tones, heavy shadows
- **Quote Tone**: Dark, stoic, warrior mentality — NOT cheesy or generic
- **Quote Style**: 1-2 sentences max, under 80 words, metaphors from nature/war/fire/storms
- **Video Dimensions**: 1080×1350 (4:5 portrait, optimized for Instagram Reels)
- **Video Duration**: 15 seconds
- **Video FPS**: 24
- **Music Genre**: Phonk, slowed beats, dark atmospheric tracks
- **Brand Handle**: @itsboldfist
- **Hashtags**: 20 curated tags including #motivation, #stoic, #darkfantasy, #berserk, #mindset, #grindset, etc.

---

## 🎬 Video Effects Breakdown

| Effect | Timing | Details |
|---|---|---|
| **Ken Burns Zoom** | 0s → 15s | Slow 1.0x → 1.10x zoom + sine-wave breathing pulse (0.008 amplitude) |
| **Camera Shake** | Continuous | Random 1px jitter, seeded per-frame for consistency |
| **Vignette** | Always on | Radial dark gradient from edges, alpha overlay (200/255 max opacity) |
| **Film Grain** | Every frame | Gaussian noise (σ=12), re-randomized each frame |
| **Flash Pulse** | 1.8s–2.3s, 9.5s–10s | White flash at text reveal (25% intensity), subtle midpoint pulse (8%) |
| **Glitch/RGB Split** | 1.3s–1.6s, 11.8s–12.1s | Red channel shift right, blue shift left + horizontal scan line displacement |
| **Fade In** | 0s–0.8s | Video opacity fade in |
| **Fade Out** | 14s–15s | Video opacity fade out |
| **Audio Fade In** | 0s–1.0s | Music volume fade in |
| **Audio Fade Out** | 13s–15s | Music volume fade out |

---

## 🌍 Deployment Options

### Option 1: GitHub Actions (Recommended — Free, 24/7)
- Push code to a **private GitHub repo**
- Add all API keys as **GitHub repository secrets**
- The workflow auto-runs at 9 AM and 7 PM IST daily
- Zero cost, zero infrastructure

### Option 2: Local (Windows Task Scheduler)
- Set up a Windows Scheduled Task
- Runs `python main.py` at specified times
- Requires PC to be on

---

## 🧠 Smart Features

1. **Auto-replenishment**: When all quotes are used up, automatically generates 10 new ones via Gemini AI
2. **Fallback chain**: Gemini primary → Gemini fallback model → hardcoded quotes
3. **Multi-platform publishing**: Publishes to both Instagram AND YouTube in one run
4. **Token type auto-detection**: Automatically detects Instagram vs Facebook API tokens
5. **Round-robin music rotation**: Tracks all used songs in Google Sheets (`Music_History` tab) — picks only from unused tracks, resets when all 9 have played. Persists across GitHub Actions runs. Falls back to local JSON tracking for offline dev.
6. **White border removal**: Post-processes AI images to remove any white borders
7. **Resilient uploads**: Google Drive primary → tmpfiles.org fallback for video hosting
8. **Partial success handling**: Marks quote as complete if at least one platform succeeds
9. **Dry-run mode**: `--dry-run` flag generates content without uploading (for testing)
10. **Cross-platform fonts**: Tries project font → Linux system fonts → Windows fonts
11. **Auto-cleanup**: Deletes temp files from Drive and local disk after publishing

---

## 📊 Key Numbers

| Metric | Value |
|---|---|
| Total service modules | 8 |
| API integrations | 7 (Gemini ×2, Sheets, Drive, Instagram, YouTube, tmpfiles) |
| Video effects | 6 cinematic effects + 4 audio/video fades |
| Daily posts | 2 (9 AM + 7 PM IST) |
| Music tracks available | 9 |
| Hashtags per post | 20 (Instagram), 11 (YouTube) |
| Video resolution | 1080×1350 (4:5 portrait) |
| Video duration | 15 seconds |
| Lines of Python code | ~1,000+ across all modules |
| Fallback mechanisms | 6 (quote fallback, image model fallback, drive fallback, font fallback, token type detection, music history Sheets→JSON fallback) |

---

## 💡 Summary for X Thread

**MIND CRAFT** is a solo-built, fully automated AI content pipeline that generates dark fantasy motivational videos (Instagram Reels + YouTube Shorts) — using **Gemini AI for both the quotes AND the artwork**, **MoviePy for cinematic video effects**, **Google Sheets as the database**, **Google Drive for temp hosting**, and **GitHub Actions for 24/7 free serverless automation**. It posts twice daily, handles everything from quote generation to publishing, and has 5 fallback mechanisms to ensure it never fails silently. Built entirely in Python with zero monthly costs.
