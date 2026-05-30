"""OpenAI gpt-image-1 image generation for stat-card style LinkedIn images.

Best when you want short accurate text rendered in the image (company names,
big numbers, dates). Comfy is better for pure mood/atmospheric shots.

API: https://platform.openai.com/docs/api-reference/images/create
"""
import os
import sys
import re
import base64
import hashlib
import requests
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import OPENAI_API_KEY, OPENAI_IMAGE_MODEL, IMAGES_DIR, draft_dir


STAT_CARD_PROMPT_TEMPLATE = """A bold editorial LinkedIn news-card graphic, 1024x1024.

Three text elements rendered as designed typography:
- Top: short bold headline in white sans-serif, 3 to 6 words max: "{headline}"
- Center: huge accent-colored number, dominant visual element: "{big_number}"
- Bottom: small italic caption with source: "{caption}"

Visual direction for this draft: {visual_theme}

Requirements: premium technology editorial design, crisp typography hierarchy, lots of negative space, abstract geometric accent shapes only (no people, no faces, no recognizable buildings or logos). Keep the same strong content density and square size, but make the color palette, background treatment, composition, and theme noticeably different from previous cards. No additional text beyond the three strings provided."""

VISUAL_THEMES = [
    "midnight navy background with electric cyan accents, thin circuit-line geometry, high-contrast newsroom feel",
    "deep emerald-to-black gradient with warm gold accent number, subtle glass panels, premium finance-terminal aesthetic",
    "charcoal background with magenta and violet neon accents, diagonal split layout, energetic AI lab atmosphere",
    "warm off-black and burnt orange palette, soft radial spotlight, bold magazine-cover composition",
    "ice-blue and silver palette on near-white frosted glass background, clean enterprise research-note feel",
    "black-to-crimson gradient with red alert accents, sharp angular shapes, breaking-news urgency without clutter",
    "deep purple space-gradient with teal highlights, abstract data-orbit arcs, futuristic but restrained",
    "matte graphite background with lime-green terminal accents, minimal developer-tool dashboard aesthetic",
]


def _theme_for_draft(draft_id: str) -> str:
    digest = hashlib.sha256(draft_id.encode("utf-8")).digest()
    return VISUAL_THEMES[digest[0] % len(VISUAL_THEMES)]


_PROMPT_FILE = Path(__file__).resolve().parent.parent / "AGENT_PROMPT.md"


def _load_image_prompt() -> str | None:
    """Read the IMAGE section of AGENT_PROMPT.md fresh every call.
    Returns None if file or markers missing; caller falls back to hardcoded template.
    """
    try:
        content = _PROMPT_FILE.read_text()
    except FileNotFoundError:
        return None
    start = "<!-- IMAGE:START -->"
    end = "<!-- IMAGE:END -->"
    if start not in content or end not in content:
        return None
    return content.split(start, 1)[1].split(end, 1)[0].strip()


def generate_image_openai(
    draft_id: str,
    headline: str,
    big_number: str,
    caption: str,
    size: str = "1024x1024",
) -> dict:
    """Generate an editorial stat card via OpenAI gpt-image-1.

    Returns dict with draft_id and image_path.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set — required for gpt-image-1")

    template = _load_image_prompt() or STAT_CARD_PROMPT_TEMPLATE
    prompt = template.format(
        headline=headline.strip(),
        big_number=big_number.strip(),
        caption=caption.strip(),
        visual_theme=_theme_for_draft(draft_id),
    )

    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_IMAGE_MODEL,
            "prompt": prompt,
            "size": size,
            "n": 1,
        },
        timeout=120,
    )
    data = r.json()
    if "data" not in data or not data["data"]:
        raise RuntimeError(f"OpenAI image error: {data}")

    item = data["data"][0]
    # Response is b64 by default
    if "b64_json" in item:
        img_bytes = base64.b64decode(item["b64_json"])
    elif "url" in item:
        img_bytes = requests.get(item["url"], timeout=30).content
    else:
        raise RuntimeError(f"Unknown image payload shape: {item}")

    ddir = draft_dir(draft_id)
    image_path = ddir / "image.png"
    image_path.write_bytes(img_bytes)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", headline[:50]).strip("_")
    archive_path = IMAGES_DIR / f"{draft_id}_{slug}.png"
    archive_path.write_bytes(img_bytes)

    return {
        "draft_id": draft_id,
        "image_path": str(image_path),
        "image_archive": str(archive_path),
        "provider": "gpt-image-1",
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("draft_id")
    p.add_argument("--headline", required=True)
    p.add_argument("--big-number", required=True)
    p.add_argument("--caption", required=True)
    args = p.parse_args()
    result = generate_image_openai(
        args.draft_id, args.headline, args.big_number, args.caption
    )
    import json as _json
    print(_json.dumps(result, indent=2))
