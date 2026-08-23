"""Generate concise, original quotes via the Gemini API.

Two styles are supported:
  - "vivid": war/fire/nature-metaphor imagery — this channel's proven top performers.
  - "calm":  plainspoken, unsentimental observational lines (no metaphor vocabulary).
"""
import requests

import config


# Only applies to the "calm" style — vivid quotes are allowed (expected) to use this vocabulary.
_CLICHE_TERMS = (
    "lion", "lions", "wolf", "wolves", "sheep", "storm", "storms",
    "sword", "swords", "blade", "blades", "fire", "flames", "forged",
    "warrior", "warriors", "battle", "battles", "greatness", "grind",
    "hustle", "pain",
)

# Applies to both styles — these exact stock phrases are dead regardless of vocabulary.
_DEAD_PHRASES = (
    "doesn't ask permission", "does not ask permission", "they buried you",
    "they doubted you", "they can't break", "they cannot break",
    "born to fight", "never give up", "never quit", "comfort is the enemy",
    "opinions of", "lose sleep over",
)


def _is_usable_quote(quote, style="calm"):
    """Keep concise lines while rejecting stock motivational language.

    The vivid-vocabulary ban only applies to the "calm" style — vivid quotes
    are expected (and proven, per channel analytics) to use that imagery.
    """
    normalized = " ".join(quote.split()).lower()
    words = normalized.split()

    if not 10 < len(normalized) < 200 or not 4 <= len(words) <= 28:
        return False

    if style == "calm" and any(term in words for term in _CLICHE_TERMS):
        return False

    return not any(phrase in normalized for phrase in _DEAD_PHRASES)


_VIVID_PROMPT_TEMPLATE = """Generate exactly {count} short, punchy lines for a dark, cinematic self-improvement channel.

Rules:
- Each quote must be 1-2 sentences, 4-28 words total
- Raw, vivid, and direct — hit hard in few words
- Use concrete imagery from nature, war, fire, storms, wolves, blades, forges, mountains
- No attribution, no author names, no quotation marks
- Each quote separated by |||
- Tone: dark, stoic, warrior mentality — earned and cinematic, not cheesy or generic
- Avoid tired stock phrases like "never give up", "comfort is the enemy", or "opinions of sheep" — the imagery should feel fresh, not recycled

Examples of the style I want:
- The storm rages, but the mountain endures.
- Let your fury be a wildfire. Leave nothing but ash where doubt used to stand.
- The battlefield cares nothing for your fear, only for your next step.
- The forge demands heat. Let your trials shape the edge.
- A blade left unused still dulls. Purpose is sharpened by motion.

Now generate {count} unique quotes in that style, separated by |||"""

_CALM_PROMPT_TEMPLATE = """Generate exactly {count} short, punchy lines for a dark, cinematic self-improvement channel.

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


def generate_story_quotes(count=10, style="vivid"):
    """Generate short, impactful quotes using Gemini API in the given style."""
    template = _VIVID_PROMPT_TEMPLATE if style == "vivid" else _CALM_PROMPT_TEMPLATE
    prompt = template.format(count=count)

    url = f"https://generativelanguage.googleapis.com/v1beta/{config.GEMINI_TEXT_MODEL}:generateContent?key={config.GEMINI_API_KEY}"

    try:
        resp = requests.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.9, "maxOutputTokens": 2048},
        }, timeout=120)
        data = resp.json()

        if "error" in data:
            print(f"Gemini text error: {data['error'].get('message', '')}")
            return _fallback_quotes(style)

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        quotes = [quote.strip() for quote in text.split("|||") if quote.strip()]
        quotes = [quote for quote in quotes if _is_usable_quote(quote, style=style)]

        if len(quotes) < 3:
            print(f"Got too few usable {style} quotes from Gemini, using fallbacks.")
            return _fallback_quotes(style)

        print(f"Generated {len(quotes)} {style} quotes via Gemini.")
        return quotes[:count]

    except Exception as exc:
        print(f"Quote generation failed: {exc}")
        return _fallback_quotes(style)


def generate_quote_batch(count=10, vivid_ratio=None):
    """Generate a batch of quotes split between vivid and calm styles.

    Returns a list of (quote_text, style) tuples. `vivid_ratio` defaults to
    config.QUOTE_STYLE_VIVID_RATIO — the fraction of the batch generated in
    the vivid style.
    """
    if vivid_ratio is None:
        vivid_ratio = config.QUOTE_STYLE_VIVID_RATIO

    vivid_count = round(count * vivid_ratio)
    calm_count = count - vivid_count

    batch = []
    if vivid_count > 0:
        batch += [(q, "vivid") for q in generate_story_quotes(count=vivid_count, style="vivid")]
    if calm_count > 0:
        batch += [(q, "calm") for q in generate_story_quotes(count=calm_count, style="calm")]

    return batch


def _fallback_quotes(style="calm"):
    """Hardcoded fallback quotes in case the API fails."""
    if style == "vivid":
        return [
            "The storm rages, but the mountain endures.",
            "Let your fury be a wildfire. Leave nothing but ash where doubt used to stand.",
            "The battlefield cares nothing for your fear, only for your next step.",
            "The forge demands heat. Let your trials shape the edge.",
            "A blade left unused still dulls. Purpose is sharpened by motion.",
            "The wolf does not explain the hunt to the herd.",
            "Every scar on the mountain is a record of what it survived.",
            "The fire does not apologize for the warmth it took to make.",
            "A sword resting in its sheath still belongs to the war.",
            "The tide does not ask the shore for permission to return.",
        ]
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
