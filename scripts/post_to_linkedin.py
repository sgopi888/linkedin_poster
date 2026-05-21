import sys
import json
import time
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import draft_dir
from linkedin_auth import get_access_token


def _atomic_write(path: Path, content: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    tmp.replace(path)


def publish_draft(draft_id: str) -> dict:
    ddir = draft_dir(draft_id)
    post_path = ddir / "post.txt"
    image_path = ddir / "image.png"
    meta_path = ddir / "meta.json"

    if not post_path.exists():
        raise FileNotFoundError(f"No post for draft_id={draft_id}")

    post_text = post_path.read_text()
    has_image = image_path.exists()

    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }

    me = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers).json()
    person_urn = f"urn:li:person:{me['sub']}"

    asset = None
    if has_image:
        register = requests.post(
            "https://api.linkedin.com/v2/assets?action=registerUpload",
            headers=headers,
            json={
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": person_urn,
                    "serviceRelationships": [
                        {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
                    ],
                }
            },
        ).json()
        upload_url = register["value"]["uploadMechanism"][
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
        ]["uploadUrl"]
        asset = register["value"]["asset"]
        with open(image_path, "rb") as img:
            requests.put(
                upload_url,
                data=img,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "image/png"},
            )
        time.sleep(5)

    share_content = {
        "shareCommentary": {"text": post_text},
        "shareMediaCategory": "IMAGE" if asset else "NONE",
    }
    if asset:
        share_content["media"] = [{
            "status": "READY",
            "description": {"text": "AI-generated image"},
            "media": asset,
            "title": {"text": "AI Agents"},
        }]

    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json={
            "author": person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {"com.linkedin.ugc.ShareContent": share_content},
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        },
    )

    ok = resp.status_code in (200, 201)
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        meta["status"] = "posted" if ok else "post_failed"
        meta["linkedin_response_status"] = resp.status_code
        meta["linkedin_response"] = resp.text[:500]
        _atomic_write(meta_path, json.dumps(meta, indent=2))

    return {
        "draft_id": draft_id,
        "status": "posted" if ok else "post_failed",
        "http_status": resp.status_code,
        "response": resp.text,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: post_to_linkedin.py <draft_id>")
        sys.exit(1)
    result = publish_draft(sys.argv[1])
    print(json.dumps(result, indent=2))
