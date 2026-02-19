"""
services/youtube.py — Upload Shorts to YouTube via YouTube Data API v3.

Uses OAuth2 with a refresh token for automated uploads.
The refresh token is obtained once locally, then stored as a GitHub secret.
"""
import os
import json
import requests
import config


def _get_access_token():
    """
    Get a fresh access token using the YouTube refresh token.
    YouTube API requires OAuth2 (not service accounts) for video uploads.
    """
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": config.YT_CLIENT_ID,
        "client_secret": config.YT_CLIENT_SECRET,
        "refresh_token": config.YT_REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }, timeout=30)

    data = resp.json()
    if "access_token" not in data:
        raise Exception(f"Failed to refresh YouTube token: {data}")
    
    return data["access_token"]


def upload_short(video_path, quote_text):
    """
    Upload a video as a YouTube Short.
    
    - Title: first 90 chars of quote
    - Description: full quote + hashtags
    - Category: 22 (People & Blogs)
    - Privacy: public
    - Shorts: enabled by adding #Shorts tag
    
    Returns (video_id, video_url) on success.
    """
    if not config.YT_REFRESH_TOKEN:
        print("⚠️ No YouTube credentials configured. Skipping YouTube upload.")
        return None, None

    access_token = _get_access_token()

    # Build metadata
    title = quote_text[:90] if len(quote_text) <= 90 else quote_text[:87] + "..."
    description = (
        f"{quote_text}\n\n"
        f"🔥 Follow for daily motivation!\n\n"
        f"#Shorts #Motivation #Stoic #DarkFantasy #Berserk #Mindset "
        f"#Grindset #NeverGiveUp #Warrior #MindCraft #DailyMotivation"
    )

    metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "22",
            "tags": ["Shorts", "motivation", "stoic", "berserk", "mindset",
                     "grindset", "warrior", "dark fantasy", "quotes"],
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "shortsRenderingEnabled": True,
        },
    }

    # Step 1: Start resumable upload
    file_size = os.path.getsize(video_path)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length": str(file_size),
        "X-Upload-Content-Type": "video/mp4",
    }

    init_resp = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        headers=headers,
        json=metadata,
        timeout=30,
    )

    if init_resp.status_code != 200:
        raise Exception(f"YouTube upload init failed: {init_resp.status_code} — {init_resp.text}")

    upload_url = init_resp.headers.get("Location")
    if not upload_url:
        raise Exception("No upload URL returned by YouTube API")

    # Step 2: Upload the video file
    with open(video_path, "rb") as f:
        upload_resp = requests.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "video/mp4",
                "Content-Length": str(file_size),
            },
            data=f,
            timeout=300,
        )

    if upload_resp.status_code not in (200, 201):
        raise Exception(f"YouTube upload failed: {upload_resp.status_code} — {upload_resp.text}")

    data = upload_resp.json()
    video_id = data.get("id", "")
    video_url = f"https://youtube.com/shorts/{video_id}"

    print(f"✅ YouTube Short uploaded: {video_url}")
    return video_id, video_url
