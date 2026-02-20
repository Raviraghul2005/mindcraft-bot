"""
main.py — MIND CRAFT Pipeline Orchestrator

Runs the full pipeline:
  1. Get/generate quote from Google Sheet
  2. Generate Berserk manga-style image via Gemini
  3. Overlay quote text on image
  4. Create video with effects + music
  5. Upload to Google Drive → Instagram Reels + YouTube Shorts
  6. Mark row as Complete + cleanup

Usage:
  python main.py              # Full pipeline
  python main.py --dry-run    # Skip upload + don't mark complete
"""
import os
import sys
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
            new_quotes = quote_gen.generate_story_quotes(count=10)
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
    image_path = image_gen.generate_image(quote=quote_text)
    print()
    
    # ---- Step 3: Overlay quote text ----
    print("✍️  Overlaying quote text on image...")
    quote_image_path = image_overlay.overlay_quote(image_path, quote_text)
    print()
    
    # ---- Step 4: Create video ----
    print("🎬 Creating video with effects and music...")
    music_track = video.get_music_track(row_index)
    video_path = video.create_video(quote_image_path, music_track)
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
        sheets.mark_complete(sheet, row_index)
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
