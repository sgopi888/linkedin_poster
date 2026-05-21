"""OpenAI gpt-image-1 image generation for stat-card style LinkedIn images.

Best when you want short accurate text rendered in the image (company names,
big numbers, dates). Comfy is better for pure mood/atmospheric shots.

API: https://platform.openai.com/docs/api-reference/images/create
"""
import os
import sys
import re
import base64
import requests
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import OPENAI_API_KEY, OPENAI_IMAGE_MODEL, IMAGES_DIR, draft_dir


STAT_CARD_PROMPT_TEMPLATE = """A clean editorial graphic with three text elements rendered as designed typography.

Composition:
- Dark gradient background, deep navy fading to graphite, with subtle dot texture
- At the top, a bold sans-serif title: "{headline}"
- In the center, a very large number in a bright accent color: "{big_number}"
- At the bottom, small italic source caption: "{caption}"

Style: minimalist modern editorial design, similar to a magazine chart card. Clean typography. Lots of whitespace. Abstract geometric shapes only. No people, no faces, no recognizable buildings or brand marks. No additional text beyond the three strings shown."""


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

    prompt = STAT_CARD_PROMPT_TEMPLATE.format(
        headline=headline.strip(),
        big_number=big_number.strip(),
        caption=caption.strip(),
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
