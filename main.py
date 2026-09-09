"""
main.py — MIND CRAFT Pipeline Orchestrator

Runs the full pipeline:
  1. Get/generate quote from Google Sheet
  2. Generate Berserk manga-style image via Gemini/Pollinations (composition rotates for variety)
  3. Build animated quote text + follow-CTA overlay layers
  4. Create video with effects + music (text/CTA composited & animated per-frame)
  5. Upload to Google Drive → Instagram Reels + YouTube Shorts
  6. Mark row as Complete + cleanup

Usage:
  python main.py              # Full pipeline
  python main.py --dry-run    # Skip upload + don't mark complete
"""
import os
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
import config
from services import sheets, quote_gen, image_gen, image_overlay, video, drive_upload, instagram, youtube


def main():
    parser = argparse.ArgumentParser(description="MIND CRAFT — Automated Motivational Reels")
    parser.add_argument("--dry-run", action="store_true", help="Generate locally, skip uploads")
    args = parser.parse_args()
    
    dry_run = args.dry_run
    if dry_run:
        print("🧪 DRY RUN MODE — will not upload or mark complete.\n")
    
    # ---- Step 0: Validate config ----
    print("⚙️  Validating configuration...")
    config.validate(dry_run=dry_run)
    print("✅ Config OK.\n")
    
    # ---- Step 1: Get next quote ----
    quote_text = None
    row_index = 2
    sheet = None
    
    try:
        print("📋 Fetching next quote from Google Sheets...")
        client = sheets.get_client()
        quote_text, row_index, sheet = sheets.get_next_quote(client)
        
        if not quote_text:
            print("🔄 All rows complete. Auto-generating new quotes...")
            new_quotes = quote_gen.generate_quote_batch(count=10)
            sheets.append_quotes(sheet, new_quotes)
            quote_text, row_index, sheet = sheets.get_next_quote(client)
    except Exception as e:
        if dry_run:
            print(f"⚠️ Google Sheets unavailable ({e}). Using sample quote for dry-run.")
        else:
            raise
    
    if not quote_text:
        if dry_run:
            quote_text = "A lion doesn't lose sleep over the opinions of sheep."
        else:
            print("❌ No quote available. Exiting.")
            sys.exit(1)
    
    # ---- Step 2: Generate image ----
    print("🎨 Generating image relevant to the quote...")
    composition = image_gen.pick_composition(row_index)
    image_path = image_gen.generate_image(quote=quote_text, composition=composition)
    print()

    # ---- Step 3: Build animated quote text + follow-CTA overlay layers ----
    print("✍️  Preparing animated quote text overlay...")
    text_layer = image_overlay.build_text_layer(quote_text, config.VIDEO_WIDTH, config.VIDEO_HEIGHT)
    cta_layer = image_overlay.build_cta_layer(config.VIDEO_WIDTH, config.VIDEO_HEIGHT)
    quote_image_path = image_overlay.save_preview(image_path, text_layer, cta_layer)
    print()

    # ---- Step 4: Create video ----
    print("🎬 Creating video with effects and music...")
    # Pass sheets client for music history persistence (works on GitHub Actions)
    sheets_client = None
    try:
        sheets_client = sheets.get_client()
    except Exception:
        pass  # Will fall back to local JSON tracking
    music_track = video.get_music_track(row_index, sheets_client=sheets_client)
    video_path = video.create_video(image_path, text_layer, cta_layer, music_track)
    print()
    
    if dry_run:
        print("=" * 50)
        print("🧪 DRY RUN COMPLETE!")
        print(f"   📄 Quote image: {quote_image_path}")
        print(f"   🎥 Video: {video_path}")
        print("   ⏭️  Skipped: Drive upload, Instagram, YouTube, sheet update")
        print("=" * 50)
        return
    
    # ---- Step 5: Upload to Google Drive ----
    print("☁️  Uploading video to Google Drive...")
    file_id, video_url = drive_upload.upload_video(video_path)
    print()
    
    # ---- Step 6: Publish to Instagram ----
    print("📲 Publishing to Instagram Reels...")
    ig_success = instagram.upload_reel(video_url, quote_text)
    print()
    
    # ---- Step 6b: Upload to YouTube Shorts ----
    print("📺 Uploading to YouTube Shorts...")
    yt_id, yt_url = youtube.upload_short(video_path, quote_text)
    print()
    
    # ---- Step 7: Cleanup ----
    # Delete Drive file AFTER Instagram is done (it needs the URL during processing)
    print("🧹 Cleaning up...")
    drive_upload.delete_video(file_id)
    
    # Clean local temp files
    for f in [image_path, quote_image_path, video_path]:
        try:
            if os.path.exists(f):
                os.remove(f)
                print(f"   Removed: {f}")
        except Exception:
            pass
    
    # ---- Step 8: Mark complete ----
    # Mark complete if EITHER platform succeeded (don't block on one failing)
    if ig_success or yt_id:
        sheets.mark_complete(sheet, row_index, youtube_url=yt_url)
    else:
        print("⚠️ Both uploads failed. Row NOT marked complete.")
    
    if not ig_success:
        print("⚠️ Instagram upload failed — check IG credentials and video URL.")
    if not yt_id:
        print("⚠️ YouTube upload failed — check YT credentials.")
    
    print()
    print("=" * 50)
    print("🎉 PIPELINE COMPLETE!")
    print("=" * 50)


if __name__ == "__main__":
    main()
