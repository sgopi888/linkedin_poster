import json
import requests

# =========================================
# LOAD TOKEN
# =========================================

with open("linkedin_token.json", "r") as f:
    token_data = json.load(f)

ACCESS_TOKEN = token_data["access_token"]

# =========================================
# HEADERS
# =========================================

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "X-Restli-Protocol-Version": "2.0.0",
    "Content-Type": "application/json"
}

# =========================================
# LOAD POST TEXT
# =========================================

POST_FILE = "/home/sreekanth/Hermes/linkedin-agent/drafts/latest_post.txt"

with open(POST_FILE, "r") as f:    POST_TEXT = f.read()

# =========================================
# IMAGE PATH
# =========================================

LATEST_IMAGE_FILE = "/home/sreekanth/Hermes/linkedin-agent/drafts/latest_image.txt"

with open(LATEST_IMAGE_FILE, "r") as f:
    IMAGE_PATH = f.read().strip()

print(f"\nUsing image:\n{IMAGE_PATH}")
# =========================================
# GET USER INFO
# =========================================

me_response = requests.get(
    "https://api.linkedin.com/v2/userinfo",
    headers=headers
)

me_data = me_response.json()

print("\n=== USER INFO ===")
print(me_data)

person_urn = f"urn:li:person:{me_data['sub']}"

# =========================================
# REGISTER IMAGE UPLOAD
# =========================================

register_payload = {
    "registerUploadRequest": {
        "recipes": [
            "urn:li:digitalmediaRecipe:feedshare-image"
        ],
        "owner": person_urn,
        "serviceRelationships": [
            {
                "relationshipType": "OWNER",
                "identifier": "urn:li:userGeneratedContent"
            }
        ]
    }
}

register_response = requests.post(
    "https://api.linkedin.com/v2/assets?action=registerUpload",
    headers=headers,
    json=register_payload
)

register_data = register_response.json()

print("\n=== REGISTER RESPONSE ===")
print(register_data)

upload_url = register_data["value"]["uploadMechanism"][
    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
]["uploadUrl"]

asset = register_data["value"]["asset"]

# =========================================
# UPLOAD IMAGE
# =========================================

with open(IMAGE_PATH, "rb") as img:

    upload_response = requests.put(
        upload_url,
        data=img,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "image/png"
        }
    )

print(upload_response.text)

print("\n=== IMAGE UPLOAD STATUS ===")
print(upload_response.status_code)

# =========================================
# CREATE LINKEDIN POST
# =========================================
import time

print("\nWaiting for LinkedIn image processing...")
time.sleep(5)

post_data = {
    "author": person_urn,
    "lifecycleState": "PUBLISHED",
    "specificContent": {
        "com.linkedin.ugc.ShareContent": {
            "shareCommentary": {
                "text": POST_TEXT
            },
            "shareMediaCategory": "IMAGE",
            "media": [
                {
                    "status": "READY",
                    "description": {
                        "text": "AI-generated image"
                    },
                    "media": asset,
                    "title": {
                        "text": "AI Agents"
                    }
                }
            ]
        }
    },
    "visibility": {
        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    }
}

post_response = requests.post(
    "https://api.linkedin.com/v2/ugcPosts",
    headers=headers,
    json=post_data
)

print("\n=== POST RESPONSE ===")
print(post_response.status_code)
print(post_response.text)