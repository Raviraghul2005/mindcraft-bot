# 🚀 MIND CRAFT Deployment Guide

This guide explains how to set up **24/7 automation** for your Motivational Reel Generator.

## 🎵 Music & Quotes
*   **Music Selection**: The system now picks a **random** MP3 from the `Music/` folder.
    *   **Action**: Add more MP3 files to `Music/` for variety!
*   **Quotes**: When the Google Sheet runs out of quotes, the system **automatically generates 10 new ones**. You don't need to do anything.

---

## ☁️ 24/7 Automation (GitHub Actions)
To run this automatically at **9:00 AM IST** and **7:00 PM IST** (without keeping your PC on), follow these steps:

### 1. Create a GitHub Repository
1.  Go to [GitHub](https://github.com/new).
2.  Create a new repository named `mindcraft-bot` (or similar).
3.  Make it **Private** (recommended, since it has your custom code).

### 2. Push Code to GitHub
Open your terminal in the project folder and run:

```bash
git init
git add .
git commit -m "Initial commit - MindCraft Bot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/mindcraft-bot.git
git push -u origin main
```
*(Replace `YOUR_USERNAME` with your actual GitHub username)*

### 3. Add Secrets to GitHub
The bot needs your API keys to run in the cloud. Check your `.env` and `credentials.json` files for these values.

1.  Go to your GitHub Repo -> **Settings** -> **Secrets and variables** -> **Actions**.
2.  Click **New repository secret**.
3.  Add the following secrets (names must match exactly):

| Secret Name | Value to Paste |
|---|---|
| `GEMINI_API_KEY` | From your `.env` |
| `IG_USER_ID` | `25977985075200610` |
| `IG_ACCESS_TOKEN` | From your `.env` (the IGAA... token) |
| `YT_CLIENT_ID` | From your `.env` |
| `YT_CLIENT_SECRET` | From your `.env` |
| `YT_REFRESH_TOKEN` | From your `.env` |
| `GOOGLE_CREDENTIALS_JSON` | **IMPORTANT**: Open `credentials.json` in Notepad, copy the **entire content**, and paste it here. |
| `OPENROUTER_API_KEY` | (Optional) From your `.env` |

### 4. Verify It Works
1.  Go to the **Actions** tab in your GitHub repo.
2.  Select **Publish Motivational Reel** on the left.
3.  Click **Run workflow** -> **Run workflow** to test it immediately.
4.  If it turns ✅ Green, you are all set! It will now run automatically every day at 9 AM and 7 PM IST.

---

## 🖥️ Local Fallback (Running on your PC)
If you prefer not to use GitHub, you can use Windows Task Scheduler:
1.  Open Task Scheduler.
2.  Create Basic Task -> "MindCraft Morning".
3.  Trigger: Daily at 9 AM.
4.  Action: Start a program.
    *   Program/script: `python`
    *   Arguments: `main.py`
    *   Start in: `C:\Users\itsme\OneDrive\Desktop\MIND CRAFT`
