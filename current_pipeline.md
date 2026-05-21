# Current Pipeline — LinkedIn Poster

## Flow (today)

```
USER PROMPT (CLI arg)
   │
   ▼
run_pipeline.py  (manual orchestrator)
   │
   ├─► content_orchestrator.py
   │      ├─ research_agent()  → OpenRouter (model from env)
   │      ├─ writing_agent()   → OpenRouter (founder-style post)
   │      ├─ review_agent()    → banned-word + length check
   │      └─ writes drafts/latest_post.txt  +  data/posts/<ts>.json
   │
   ├─► image_agent.py
   │      ├─ loads drafts/latest_post.txt
   │      ├─ builds Comfy workflow (api_wan_text_to_image.json)
   │      ├─ submits to cloud.comfy.org, polls every 5s (≤5 min)
   │      └─ writes images/<ts>_<slug>.png  +  drafts/latest_image.txt
   │
   ├─► input("Post to LinkedIn? yes/no")   ← human gate
   │
   └─► post_to_linkedin.py
          ├─ reads linkedin_token.json
          ├─ /v2/userinfo → person URN
          ├─ registerUpload → PUT image → asset URN
          └─ POST /v2/ugcPosts (IMAGE share, PUBLIC)
```

Supporting:
- `oauth_linkedin.py` — one-off Flask app on :8848 to mint `linkedin_token.json`.
- `fetch_news.py` — NewsAPI puller → `data/news.json` (not wired in).
- `review_post.py` — standalone linter (duplicates orchestrator's review).
- `discord_bot.py` — empty stub.
- `generate_posts_unused.py` — dead.

## What's tedious / broken

1. **Hardcoded server paths everywhere** — `/home/sreekanth/Hermes/linkedin-agent/...` in `content_orchestrator.py`, `image_agent.py`, `post_to_linkedin.py`. Won't run on Mac without edits. → move to `config.py` (currently empty) reading from env: `BASE_DIR`, `DRAFTS_DIR`, `IMAGES_DIR`, `POSTS_DIR`, `ENV_PATH`.
2. **Manual approval gate** (`input()` in `run_pipeline.py`) blocks autonomous/cron runs. → add `--auto` flag or env `AUTO_APPROVE=1` that skips the prompt when review_agent returns no issues.
3. **LinkedIn token expires (~60 days), no refresh** — `linkedin_token.json` is written once and read raw. → store `refresh_token`, add expiry check + auto-refresh helper.
4. **No topic source for autonomous mode** — pipeline needs a CLI arg. `fetch_news.py` exists but isn't connected and has placeholder API key. → wire `fetch_news` → pick top article → feed to orchestrator.
5. **No scheduler** — nothing runs the pipeline on a cadence. → systemd timer or cron on VPS.
6. **No dedup / history check** — could re-post similar topics. → hash topic, skip if seen in last N days (`data/posts/*.json` already has timestamps).
7. **`discord_bot.py` is empty** — README claims Discord integration. Either build it or drop from README.
8. **Polling loop in `image_agent.py`** uses 5s × 60 = 5 min ceiling, often too short for Wan; no retry on transient 5xx.
9. **No `.env.example`, no `requirements.txt`** — clone-and-run on a fresh VPS is painful.
10. **Review is weak** — only banned words + length; no quality scoring, no image-text relevance check.

## Local + Server parity (proposal)

- `config.py` resolves `BASE_DIR = Path(__file__).resolve().parent`; all subpaths derived.
- `.env` per host (`.env.local`, `.env.server`), loaded via `ENV=local|server`.
- `requirements.txt` + `setup.sh` (`python -m venv .venv && pip install -r requirements.txt`).
- `.env.example` with: `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `COMFY_CLOUD_API_KEY`, `LINKEDIN_CLIENT_ID/SECRET/REDIRECT_URI`, `NEWS_API_KEY`, `AUTO_APPROVE`.

## Autonomous posting (target flow)

```
cron / systemd timer (VPS, e.g. daily 09:00)
   ▼
fetch_news.py        → picks unseen trending AI story
   ▼
content_orchestrator → research + write + review
   ▼
image_agent          → Comfy image
   ▼
auto-approve if review clean (else queue for manual review via Discord)
   ▼
post_to_linkedin     → with token-refresh
   ▼
append to data/posts/history.json
```

## Existing repos worth cloning / borrowing from

- **n8n** (self-hostable, has LinkedIn + OpenAI + cron nodes) — fastest path; wrap our scripts as a single "Execute Command" node, schedule in n8n UI.
- **Make.com / Zapier-style** — proprietary, skip.
- **`langchain-ai/langgraph`** — overkill for this DAG.
- **`appleboy/scheduled-actions` or GitHub Actions cron** — free scheduling if VPS isn't required; runner pulls repo, runs `run_pipeline.py --auto`.
- **`SocialFlow` / `Postiz` (open-source)** — full scheduler + LinkedIn auth + image queue already built; could fork and replace generator with our agent.

Recommendation: keep current scripts, add `config.py` + `--auto` + token refresh + cron on the VPS. Don't adopt a heavy framework yet — the pipeline is 5 scripts.
