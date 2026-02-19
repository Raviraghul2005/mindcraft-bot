"""
yt_auth_setup.py — One-time helper to get YouTube OAuth2 refresh token.

Run this ONCE locally:
  python yt_auth_setup.py

It will open your browser to authorize, then print the refresh token.
Save that token as YT_REFRESH_TOKEN in your .env or GitHub secret.

Prerequisites:
  1. Go to https://console.cloud.google.com/
  2. Enable the "YouTube Data API v3"
  3. Create OAuth2 credentials (Desktop app type)
  4. Download the client JSON and note client_id + client_secret
  5. Set YT_CLIENT_ID and YT_CLIENT_SECRET in your .env file
"""
import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("YT_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8090"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ Set YT_CLIENT_ID and YT_CLIENT_SECRET in your .env file first!")
    print("   Get these from Google Cloud Console → APIs → Credentials → OAuth2")
    exit(1)


class AuthHandler(BaseHTTPRequestHandler):
    """Handle the OAuth2 callback."""
    code = None

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        AuthHandler.code = query.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>Done! You can close this tab.</h1>")

    def log_message(self, format, *args):
        pass  # Suppress logs


def main():
    # Step 1: Open browser for authorization
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    })

    print("🌐 Opening browser for YouTube authorization...")
    webbrowser.open(auth_url)

    # Step 2: Wait for callback
    server = HTTPServer(("localhost", 8090), AuthHandler)
    server.handle_request()

    code = AuthHandler.code
    if not code:
        print("❌ No authorization code received.")
        return

    # Step 3: Exchange code for tokens
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    })

    data = resp.json()
    if "refresh_token" not in data:
        print(f"❌ Failed to get refresh token: {data}")
        return

    refresh_token = data["refresh_token"]

    print("\n" + "=" * 60)
    print("✅ SUCCESS! Here's your YouTube refresh token:\n")
    print(f"   {refresh_token}")
    print("\n📋 Add this to your .env file:")
    print(f'   YT_REFRESH_TOKEN={refresh_token}')
    print("\n📋 And to GitHub Secrets:")
    print(f"   Secret name: YT_REFRESH_TOKEN")
    print(f"   Secret value: {refresh_token}")
    print("=" * 60)


if __name__ == "__main__":
    main()
