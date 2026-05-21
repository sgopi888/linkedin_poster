import os
import json
import uuid
import time
import requests
from dotenv import load_dotenv

# =========================================
# LOAD ENV
# =========================================

load_dotenv(dotenv_path="/home/sreekanth/Hermes/linkedin-agent/.env")

COMFY_API_KEY = os.getenv("COMFY_CLOUD_API_KEY")

WORKFLOW_FILE = "/home/sreekanth/Hermes/linkedin-agent/scripts/workflows/api_wan_text_to_image.json"

POST_TEXT_FILE = "drafts/latest_post.txt"

OUTPUT_IMAGE = "drafts/generated_image.png"

# =========================================
# LOAD POST
# =========================================

with open(POST_TEXT_FILE, "r") as f:
    post_text = f.read()

# =========================================
# LOAD WORKFLOW
# =========================================

with open(WORKFLOW_FILE, "r") as f:
    workflow = json.load(f)

# =========================================
# PROMPT
# =========================================

PROMPT = f"""
Create a cinematic LinkedIn image.

STYLE:
- futuristic AI aesthetics
- premium
- elegant
- sophisticated
- cinematic lighting
- autonomous AI systems
- neural memory
- founder energy
- world-class technology company branding

CONTEXT:
{post_text}

High quality. Professional. Visually striking.
"""

print("\n=== PROMPT ===\n")
print(PROMPT)

# =========================================
# FIND PROMPT NODE
# =========================================

prompt_node_found = False

for node_id, node_data in workflow.items():

    if (
        node_data.get("class_type") == "WanTextToImageApi"
    ):

        workflow[node_id]["inputs"]["prompt"] = PROMPT

        print(f"\nUpdated prompt node: {node_id}")

        prompt_node_found = True
        break

if not prompt_node_found:
    raise Exception("No WanTextToImageApi node found.")


# =========================================
# SUBMIT WORKFLOW
# =========================================

payload = {
    "prompt": workflow,
    "client_id": str(uuid.uuid4()),
    "extra_data": {
        "api_key_comfy_org": COMFY_API_KEY
    }
}

print("\n=== SUBMITTING WORKFLOW ===\n")

response = requests.post(
    "https://cloud.comfy.org/api/prompt",
    headers={
        "X-API-Key": COMFY_API_KEY,
        "Content-Type": "application/json"
    },
    json=payload
)

result = response.json()

print(result)

if "prompt_id" not in result:
    raise Exception(f"Workflow submission failed: {result}")

prompt_id = result["prompt_id"]

print(f"\nPrompt ID: {prompt_id}")

# =========================================
# POLL FOR RESULT
# =========================================

history_url = f"https://cloud.comfy.org/api/jobs/{prompt_id}"

print("\n=== WAITING FOR IMAGE ===\n")

image_url = None

for _ in range(60):

    time.sleep(5)

    history_response = requests.get(
        history_url,
        headers={
            "X-API-Key": COMFY_API_KEY
        }
    )

    history = history_response.json()

    print(history)

    if history.get("status") == "completed":

        outputs = history.get("outputs", {})

        for node_output in outputs.values():

            if "images" in node_output:

                image_data = node_output["images"][0]

                filename = image_data["filename"]
                subfolder = image_data.get("subfolder", "")
                file_type = image_data.get("type", "output")

                print("\n=== IMAGE DATA ===\n")
                print(image_data)

                download_url = (
                    f"https://cloud.comfy.org/api/view?"
                    f"filename={filename}&subfolder={subfolder}&type={file_type}"
                )

                print("\n=== DOWNLOAD URL ===\n")
                print(download_url)

                image_response = requests.get(
                    download_url,
                    headers={
                        "X-API-Key": COMFY_API_KEY
                    },
                    allow_redirects=True
                )

                from datetime import datetime
                import re

                # =========================================
                # CREATE SAFE FILENAME
                # =========================================

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                title_snippet = re.sub(
                    r'[^a-zA-Z0-9]+',
                    '_',
                    post_text[:50]
                ).strip("_")

                OUTPUT_IMAGE = (
                    f"/home/sreekanth/Hermes/linkedin-agent/images/"
                    f"{timestamp}_{title_snippet}.png"
                )
                with open(OUTPUT_IMAGE, "wb") as f:
                    f.write(image_response.content)

                print(f"\nSaved image to: {OUTPUT_IMAGE}")
                LATEST_IMAGE_FILE = "/home/sreekanth/Hermes/linkedin-agent/drafts/latest_image.txt"

                with open(LATEST_IMAGE_FILE, "w") as f:
                    f.write(OUTPUT_IMAGE)

                print(f"\nSaved latest image path to: {LATEST_IMAGE_FILE}")

                image_url = OUTPUT_IMAGE

                break
                
    if image_url:
        break

if not image_url:
    raise Exception("Image generation timed out.")

print("\n=== IMAGE URL ===\n")
print(image_url)
