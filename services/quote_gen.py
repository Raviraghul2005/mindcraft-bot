"""Generate concise, original quotes via the Gemini API."""
import requests

import config


_CLICHE_TERMS = (
    "lion", "lions", "wolf", "wolves", "sheep", "storm", "storms",
    "sword", "swords", "blade", "blades", "fire", "flames", "forged",
    "warrior", "warriors", "battle", "battles", "greatness", "grind",
    "hustle", "pain",
)
_CLICHE_PHRASES = (
    "doesn't ask permission", "does not ask permission", "they buried you",
    "they doubted you", "they can't break", "they cannot break",
    "born to fight", "never give up", "never quit", "comfort is the enemy",
    "opinions of", "lose sleep over",
)


def _is_usable_quote(quote):
    """Keep concise lines while rejecting stock motivational language."""
    normalized = " ".join(quote.split()).lower()
    words = normalized.split()

    if not 10 < len(normalized) < 200 or not 4 <= len(words) <= 28:
        return False

    if any(term in words for term in _CLICHE_TERMS):
        return False

    return not any(phrase in normalized for phrase in _CLICHE_PHRASES)


def generate_story_quotes(count=10):
    """Generate short, impactful quotes using Gemini API."""
    prompt = f"""Generate exactly {count} short, punchy lines for a dark, cinematic self-improvement channel.

Rules:
- Each quote must be 1-2 sentences, 4-28 words total
- Make each line precise, plainspoken, and highly impactful
- Write observations that feel earned, not speeches or slogans
- Draw from ordinary effort: repetition, restraint, unfinished work, doubt, time, attention, and recovery
- Let the reader reach the conclusion; do not explain the lesson
- Avoid commands and direct address such as "you need to", "become", "fight", or "never quit"
- Never use lions, wolves, sheep, storms, swords, blades, fire, warriors, battles, grinding, hustle, greatness, or pain
- Never use an unnamed enemy such as "they" or "people" to manufacture conflict
- No attribution, no author names, no quotation marks
- Each quote separated by |||
- Tone: calm, unsentimental, disciplined, and dark without being theatrical

Examples of the style I want:
- Some progress is quiet enough to be mistaken for nothing.
- The work got easier when it stopped needing to feel important.
- You can be uncertain and still be consistent.
- Not every hard day needs a breakthrough. Some only need completion.
- Discipline is often making tomorrow slightly less difficult.

Now generate {count} unique quotes in that style, separated by |||"""

    url = f"https://generativelanguage.googleapis.com/v1beta/{config.GEMINI_TEXT_MODEL}:generateContent?key={config.GEMINI_API_KEY}"

    try:
        resp = requests.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.9, "maxOutputTokens": 2048},
        }, timeout=120)
        data = resp.json()

        if "error" in data:
            print(f"Gemini text error: {data['error'].get('message', '')}")
            return _fallback_quotes()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        quotes = [quote.strip() for quote in text.split("|||") if quote.strip()]
        quotes = [quote for quote in quotes if _is_usable_quote(quote)]

        if len(quotes) < 3:
            print("Got too few usable quotes from Gemini, using fallbacks.")
            return _fallback_quotes()

        print(f"Generated {len(quotes)} quotes via Gemini.")
        return quotes[:count]

    except Exception as exc:
        print(f"Quote generation failed: {exc}")
        return _fallback_quotes()


def _fallback_quotes():
    """Hardcoded fallback quotes in case the API fails."""
    return [
        "Some progress is quiet enough to be mistaken for nothing.",
        "The work got easier when it stopped needing to feel important.",
        "You can be uncertain and still be consistent.",
        "Not every hard day needs a breakthrough. Some only need completion.",
        "Discipline is often making tomorrow slightly less difficult.",
        "A routine is a promise made before the mood arrives.",
        "The result changed after the excuses became boring.",
        "Most difficult things become ordinary through repetition.",
        "There is no dramatic version of showing up again.",
        "Finish the day before you judge it.",
    ]
