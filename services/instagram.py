"""
services/instagram.py — Upload video to Instagram Reels with caption + hashtags.

Uses the Instagram Graph API via the Facebook Graph API.
Supports both Facebook Page tokens and Instagram API tokens.
Uses polling instead of sleep() to wait for media container processing.
"""
import time
import requests
import config


# Instagram API base URL (works with Instagram API tokens)
INSTAGRAM_API_BASE = "https://graph.instagram.com"
# Facebook Graph API base URL (works with Facebook Page tokens)
FACEBOOK_API_BASE = "https://graph.facebook.com/v21.0"


def _build_caption(quote):
    """Build the Instagram caption with quote + handle + hashtags."""
    caption = f'"{quote}"\n\n'
    caption += f"Follow {config.INSTAGRAM_HANDLE} for daily motivation\n\n"
    caption += config.HASHTAGS
    return caption


def _detect_token_type(access_token):
    """
    Detect if the token is an Instagram API token (starts with IGAA)
    or a Facebook Graph API token.
    """
    if access_token and access_token.startswith("IGAA"):
        return "instagram"
    return "facebook"


def _get_api_base():
    """Get the correct API base URL based on token type."""
    token_type = _detect_token_type(config.IG_ACCESS_TOKEN)
    if token_type == "instagram":
        return INSTAGRAM_API_BASE
    return FACEBOOK_API_BASE


def _wait_for_container(container_id, access_token, max_wait=120, poll_interval=5):
    """
    Poll Instagram API to wait for media container to finish processing.
    Returns True if ready, False if timed out or errored.
    """
    api_base = _get_api_base()
    status_url = f"{api_base}/{container_id}"
    params = {
        "fields": "status_code,status",
        "access_token": access_token,
    }
    
    elapsed = 0
    while elapsed < max_wait:
        resp = requests.get(status_url, params=params)
        data = resp.json()
        
        status_code = data.get("status_code", "")
        print(f"  Processing: {status_code} (waited {elapsed}s)")
        
        if status_code == "FINISHED":
            return True
        elif status_code == "ERROR":
            print(f"  Container processing failed: {data}")
            return False
        
        time.sleep(poll_interval)
        elapsed += poll_interval
    
    print(f"  Container timed out after {max_wait}s")
    return False


def upload_reel(video_url, quote):
    """
    Upload a video as an Instagram Reel with caption and hashtags.
    
    Args:
        video_url: Public URL of the video (from temp hosting)
        quote: The quote text (used to build caption)
    
    Returns:
        True if published successfully, False otherwise
    """
    if not config.IG_USER_ID or not config.IG_ACCESS_TOKEN:
        print("No Instagram credentials set. Skipping upload.")
        return False
    
    caption = _build_caption(quote)
    api_base = _get_api_base()
    token_type = _detect_token_type(config.IG_ACCESS_TOKEN)
    
    print(f"Uploading to Instagram Reels (token type: {token_type})...")
    
    # Step 1: Create media container
    create_url = f"{api_base}/{config.IG_USER_ID}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": config.IG_ACCESS_TOKEN,
    }
    
    resp = requests.post(create_url, data=payload)
    result = resp.json()
    print(f"Container response: {result}")
    
    if "id" not in result:
        print(f"Failed to create Instagram container: {result}")
        return False
    
    container_id = result["id"]
    
    # Step 2: Wait for container to finish processing
    if not _wait_for_container(container_id, config.IG_ACCESS_TOKEN):
        print("Instagram container processing failed.")
        return False
    
    # Step 3: Publish
    publish_url = f"{api_base}/{config.IG_USER_ID}/media_publish"
    publish_payload = {
        "creation_id": container_id,
        "access_token": config.IG_ACCESS_TOKEN,
    }
    
    publish_resp = requests.post(publish_url, data=publish_payload)
    publish_result = publish_resp.json()
    print(f"Publish response: {publish_result}")
    
    if "id" in publish_result:
        print(f"Reel published! ID: {publish_result['id']}")
        return True
    else:
        print(f"Publish failed: {publish_result}")
        return False
