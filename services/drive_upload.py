"""
services/drive_upload.py — Upload video to get a public URL for Instagram.

Primary: Google Drive (service account)
Fallback: file.io (free temporary file hosting, auto-deletes after download)
"""
import os
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import config


def _get_drive_service():
    """Create a Google Drive API service."""
    cred_path = config.get_google_credentials_path()
    creds = Credentials.from_service_account_file(cred_path, scopes=config.GOOGLE_SCOPES)
    return build("drive", "v3", credentials=creds)


def _get_or_create_folder(service, folder_name="mindcraft_temp"):
    """Get or create a folder in Google Drive for temporary uploads."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    files = results.get("files", [])
    
    if files:
        return files[0]["id"]
    
    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    folder = service.files().create(body=file_metadata, fields="id").execute()
    print(f"   Created Drive folder: {folder_name}")
    return folder["id"]


def _upload_to_drive(video_path):
    """Upload to Google Drive and return (file_id, public_url)."""
    service = _get_drive_service()
    folder_id = _get_or_create_folder(service)
    
    filename = os.path.basename(video_path)
    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }
    
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    
    print(f"   Uploading {filename} to Google Drive...")
    file = service.files().create(
        body=file_metadata, media_body=media, fields="id,webContentLink"
    ).execute()
    
    file_id = file["id"]
    
    # Make the file publicly accessible
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()
    
    # Use webContentLink for direct download (better for Instagram API)
    # The webContentLink provides a URL that doesn't require extra redirects
    video_url = file.get("webContentLink")
    if not video_url:
        # Fallback: add confirm=t to bypass consent screen for large files
        video_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
    print(f"   Uploaded to Drive: {video_url}")
    return file_id, video_url


def _upload_to_tmpfiles(video_path):
    """
    Fallback: Upload to tmpfiles.org (free, files last 1 hour).
    Returns (None, public_url).
    """
    print("   Uploading to tmpfiles.org (free temp hosting)...")
    with open(video_path, "rb") as f:
        resp = requests.post(
            "https://tmpfiles.org/api/v1/upload",
            files={"file": (os.path.basename(video_path), f, "video/mp4")},
            timeout=120,
        )
    
    data = resp.json()
    if data.get("status") == "success":
        # Convert the page URL to a direct download URL
        url = data["data"]["url"]
        # tmpfiles.org URLs: https://tmpfiles.org/12345/file.mp4
        # Direct URL: https://tmpfiles.org/dl/12345/file.mp4
        direct_url = url.replace("tmpfiles.org/", "tmpfiles.org/dl/", 1)
        print(f"   Uploaded: {direct_url}")
        return None, direct_url
    
    raise Exception(f"tmpfiles.org upload failed: {data}")


def upload_video(video_path):
    """
    Upload a video and return (file_id, public_url).
    Tries Google Drive first, falls back to tmpfiles.org.
    """
    # Try Google Drive first
    try:
        return _upload_to_drive(video_path)
    except Exception as e:
        print(f"   Drive upload failed: {e}")
        print("   Trying fallback upload...")
    
    # Fallback to tmpfiles.org
    return _upload_to_tmpfiles(video_path)


def delete_video(file_id):
    """Delete a video from Google Drive after Instagram has processed it."""
    if file_id is None:
        return  # Was uploaded to temp hosting, auto-deletes
    try:
        service = _get_drive_service()
        service.files().delete(fileId=file_id).execute()
        print(f"   Deleted temp file from Drive: {file_id}")
    except Exception as e:
        print(f"   Could not delete Drive file {file_id}: {e}")
