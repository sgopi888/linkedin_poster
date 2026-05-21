from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "scripts"
DRAFTS_DIR = BASE_DIR / "drafts"
IMAGES_DIR = BASE_DIR / "images"
POSTS_DIR = BASE_DIR / "data" / "posts"
WORKFLOWS_DIR = SCRIPTS_DIR / "workflows"
ENV_PATH = SCRIPTS_DIR / ".env"
TOKEN_PATH = BASE_DIR / "linkedin_token.json"

load_dotenv(dotenv_path=ENV_PATH)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")
COMFY_CLOUD_API_KEY = os.getenv("COMFY_CLOUD_API_KEY")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")


def draft_dir(draft_id: str) -> Path:
    d = DRAFTS_DIR / draft_id
    d.mkdir(parents=True, exist_ok=True)
    return d
