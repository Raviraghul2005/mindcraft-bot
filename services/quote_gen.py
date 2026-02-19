"""
services/quote_gen.py — Auto-generate short, punchy motivational quotes via Gemini.
"""
import requests
import config


def generate_story_quotes(count=10):
    """
    Generate short, punchy motivational quotes using Gemini API.
    Returns a list of quote strings (1-2 sentences each).
    """
    prompt = f"""Generate exactly {count} short, punchy motivational quotes.

Rules:
- Each quote must be 1-2 sentences MAXIMUM (under 80 words)
- Raw, powerful, and direct — hit hard in few words
- Use metaphors from nature, war, fire, storms, lions, wolves, swords
- No attribution, no author names, no quotation marks
- Each quote separated by |||
- Tone: dark, stoic, warrior mentality — NOT cheesy or generic
- Think: something a battle-scarred warrior would say before a fight

Examples of the style I want:
- The storm doesn't ask permission. Neither should you.
- A dull blade is useless. Sharpen yourself through pain.
- They buried you. They didn't know you were a seed.
- Wolves don't lose sleep over the opinions of sheep.
- The fire that forged the sword didn't ask if it would hurt.

Now generate {count} unique quotes in that style, separated by |||"""

    url = f"https://generativelanguage.googleapis.com/v1beta/{config.GEMINI_TEXT_MODEL}:generateContent?key={config.GEMINI_API_KEY}"

    try:
        resp = requests.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.9, "maxOutputTokens": 2048},
        }, timeout=120)

        data = resp.json()

        if "error" in data:
            print(f"❌ Gemini text error: {data['error'].get('message', '')}")
            return _fallback_quotes()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        quotes = [q.strip() for q in text.split("|||") if q.strip()]
        # Filter: keep only short punchy ones (under 200 chars)
        quotes = [q for q in quotes if 10 < len(q) < 200]

        if len(quotes) < 3:
            print("⚠️ Got too few quotes from Gemini, using fallbacks.")
            return _fallback_quotes()

        print(f"✅ Generated {len(quotes)} quotes via Gemini.")
        return quotes[:count]

    except Exception as e:
        print(f"❌ Quote generation failed: {e}")
        return _fallback_quotes()


def _fallback_quotes():
    """Hardcoded fallback quotes in case the API fails."""
    return [
        "The storm doesn't ask permission. Neither should you.",
        "A dull blade is useless. Sharpen yourself through pain.",
        "They buried you. They didn't know you were a seed.",
        "Wolves don't lose sleep over the opinions of sheep.",
        "The fire that forged the sword didn't ask if it would hurt.",
        "You were born to fight. Not to surrender.",
        "Comfort is the enemy of greatness.",
        "Fall seven times. Stand up eight.",
        "The lion doesn't turn around when the small dog barks.",
        "Your pain is building something they can't break.",
    ]
