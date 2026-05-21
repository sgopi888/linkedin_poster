import os
import sys
import json
import uuid
import time
import re
import requests
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import COMFY_CLOUD_API_KEY, WORKFLOWS_DIR, IMAGES_DIR, draft_dir

WORKFLOW_FILE = WORKFLOWS_DIR / "api_wan_text_to_image.json"

IMAGE_PROMPT_TEMPLATE = """
Create a cinematic LinkedIn image. ABSOLUTELY NO TEXT, NO WORDS, NO LETTERS, NO NUMBERS, NO STATS, NO HASHTAGS in the image. Pure visual mood only.

STYLE:
- futuristic AI aesthetics, premium, elegant, sophisticated
- cinematic lighting, depth of field
- abstract or scene-based visual metaphor for the topic
- world-class technology company branding aesthetic
- minimalist composition

MOOD INSPIRATION (do NOT depict literally, do NOT render any text):
{post_text}

High quality. Professional. Visually striking. Photographic or cinematic render. ZERO text overlays. ZERO captions. ZERO labels.
"""


def generate_image(draft_id: str, poll_interval: int = 5, max_polls: int = 120) -> dict:
    ddir = draft_dir(draft_id)
    post_path = ddir / "post.txt"
    if not post_path.exists():
        raise FileNotFoundError(f"No post for draft_id={draft_id}")
    post_text = post_path.read_text()

    workflow = json.loads(WORKFLOW_FILE.read_text())
    prompt = IMAGE_PROMPT_TEMPLATE.format(post_text=post_text)

    for node_id, node_data in workflow.items():
        if node_data.get("class_type") == "WanTextToImageApi":
            workflow[node_id]["inputs"]["prompt"] = prompt
            break
    else:
        raise Exception("No WanTextToImageApi node found.")

    payload = {
        "prompt": workflow,
        "client_id": str(uuid.uuid4()),
        "extra_data": {"api_key_comfy_org": COMFY_CLOUD_API_KEY},
    }

    r = requests.post(
        "https://cloud.comfy.org/api/prompt",
        headers={"X-API-Key": COMFY_CLOUD_API_KEY, "Content-Type": "application/json"},
        json=payload,
    )
    result = r.json()
    if "prompt_id" not in result:
        raise Exception(f"Workflow submission failed: {result}")
    prompt_id = result["prompt_id"]

    history_url = f"https://cloud.comfy.org/api/jobs/{prompt_id}"
    for _ in range(max_polls):
        time.sleep(poll_interval)
        history = requests.get(history_url, headers={"X-API-Key": COMFY_CLOUD_API_KEY}).json()
        if history.get("status") != "completed":
            continue

        for node_output in history.get("outputs", {}).values():
            if "images" not in node_output:
                continue
            image_data = node_output["images"][0]
            filename = image_data["filename"]
            subfolder = image_data.get("subfolder", "")
            file_type = image_data.get("type", "output")
            download_url = (
                f"https://cloud.comfy.org/api/view?"
                f"filename={filename}&subfolder={subfolder}&type={file_type}"
            )
            img = requests.get(
                download_url,
                headers={"X-API-Key": COMFY_CLOUD_API_KEY},
                allow_redirects=True,
            )

            IMAGES_DIR.mkdir(parents=True, exist_ok=True)
            title_snippet = re.sub(r"[^a-zA-Z0-9]+", "_", post_text[:50]).strip("_")
            archive_path = IMAGES_DIR / f"{draft_id}_{title_snippet}.png"
            archive_path.write_bytes(img.content)

            image_path = ddir / "image.png"
            image_path.write_bytes(img.content)

            meta_path = ddir / "meta.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                meta["image_path"] = str(image_path)
                meta["image_archive"] = str(archive_path)
                tmp = meta_path.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(meta, indent=2))
                tmp.replace(meta_path)

            return {"draft_id": draft_id, "image_path": str(image_path)}

    raise Exception("Image generation timed out.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: image_agent.py <draft_id>")
        sys.exit(1)
    result = generate_image(sys.argv[1])
    print(f"\nImage: {result['image_path']}")
