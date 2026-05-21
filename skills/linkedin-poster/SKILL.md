---
name: linkedin-poster
description: "Self-hosted LinkedIn drafting + publishing pipeline. Generate founder-style posts with AI image via OpenRouter + Comfy Cloud, store as reviewable drafts, publish on approval through the official LinkedIn v2 API. Single CLI entry point (scripts/hermes_cmd.py) with JSON in/out. Use when the user wants to draft a LinkedIn post, list/show drafts, approve or reject a draft, or publish to LinkedIn. NOT a third-party wrapper — owns its own OAuth and posts directly to api.linkedin.com."
version: 0.1.0
author: sgopi888
license: MIT
platforms: [linux, macos]
prerequisites:
  commands: [python3]
  env:
    - OPENROUTER_API_KEY
    - OPENROUTER_MODEL
    - COMFY_CLOUD_API_KEY
    - LINKEDIN_CLIENT_ID
    - LINKEDIN_CLIENT_SECRET
    - LINKEDIN_REDIRECT_URI
metadata:
  hermes:
    tags: [linkedin, social-media, content-generation, ai-image, openrouter, comfy-cloud, founder-content]
    related_skills: [xurl]
---

# linkedin-poster — Self-Hosted LinkedIn Pipeline

## Overview

A LinkedIn content pipeline you control end-to-end. Generates founder-style posts (OpenRouter / DeepSeek), pairs them with a cinematic AI image (Comfy Cloud), stores each draft as a reviewable artifact, and publishes to the authenticated user's LinkedIn feed via `api.linkedin.com/v2/ugcPosts`.

No third-party SaaS in the loop — your own LinkedIn OAuth token, your own posts.

The repo is the same code on Mac (dev) and VPS (prod); `config.BASE_DIR` resolves from `__file__`.

## When to Use

- User says "draft a LinkedIn post about X" / "write me a post on Y"
- User asks "what drafts do I have?" / "show me draft 20260520_..."
- User says "approve <draft_id>" / "post that" / "publish 20260520_..."
- User says "reject <draft_id>" / "trash that draft"

**Don't use for:** posting to X/Twitter (use `xurl`), posting to LinkedIn *company pages* (requires LinkedIn Advertising API approval — not wired), scheduling (no scheduler yet; cron is a future addition).

## Setup (one-time, per host)

```bash
cd ~/Hermes/linkedin-agent          # VPS path; on Mac it's ~/Desktop/Apps/linkedin_poster
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# Populate scripts/.env with the 6 keys listed in prerequisites.env
.venv/bin/python scripts/oauth_linkedin.py    # mints linkedin_token.json
```

## The Only Entry Point

All operations go through `scripts/hermes_cmd.py`. Always invoke via the project venv. Every command prints a single JSON object on stdout. Exit code 1 means error and the JSON has an `"error"` field.

```bash
.venv/bin/python scripts/hermes_cmd.py <command> [args]
```

| Command | Purpose | Doc |
|---|---|---|
| `draft "<topic>" [--no-image]` | Generate post + image, save as new draft | `endpoints/draft.md` |
| `publish <draft_id> [--force]` | Post a draft to LinkedIn | `endpoints/publish.md` |
| `reject <draft_id>` | Mark draft rejected | `endpoints/reject.md` |

To inspect drafts without invoking the CLI (Hermes can do this directly):

```bash
ls drafts/                       # all draft IDs (newest = highest YYYYMMDD_HHMMSS)
cat drafts/<id>/meta.json        # one draft's status + post text + image_path
```

**Load only the endpoint doc you need.** Each is small (~50 lines) and self-contained. Loading all at once wastes context.

## Installation (Hermes)

Skills live under `~/.hermes/skills/<category>/<name>/`. This skill lives inside the app repo; the simplest install is a symlink:

```bash
ln -s ~/Hermes/linkedin-agent/skills/linkedin-poster \
      ~/.hermes/skills/social-media/linkedin-poster
# Restart Hermes gateway so the new skill is picked up as a slash command.
```

After this, `/linkedin-poster` becomes available in Discord automatically.

## Typical Discord Flow

```
User:    "draft a post about agentic memory"
You:     [run: .venv/bin/python scripts/hermes_cmd.py draft "agentic memory"]
You:     [parse JSON → reply in Discord with post text + image + draft_id]
You:     [say: "Approve with `approve <id>` or reject with `reject <id>`"]

User:    "approve 20260520_212437"
You:     [run: .venv/bin/python scripts/hermes_cmd.py publish 20260520_212437]
You:     [reply "Posted ✅" or surface the error]
```

## Draft Lifecycle

```
draft   ──► publish  ──► posted
       ╲                  
        ╲─► reject  ──► rejected   (still on disk; --force to publish anyway)
```

Drafts live at `drafts/<draft_id>/{post.txt, image.png, meta.json}`. Status changes are persisted in `meta.json`.

## Key Invariants

- `draft_id` format is `YYYYMMDD_HHMMSS` (also the directory name).
- `hermes_cmd.py` is the ONLY supported integration surface. Do not import internal modules from Hermes-side code.
- `publish` on an already-posted draft is a no-op returning `{"status": "already_posted"}` — safe to retry.
- `reject` is a soft-delete: files stay on disk for audit / regenerate.

## Common Pitfalls

1. **Forgetting the venv.** Running `python scripts/hermes_cmd.py` with system Python misses `requests` / `dotenv`. Always use `.venv/bin/python`.
2. **Auto-publishing without approval.** Never run `publish` until the user explicitly says so. LinkedIn is the user's public brand.
3. **Trying to load all endpoint docs.** Read only the one you need (`endpoints/<command>.md`).
4. **Treating the LinkedIn token as eternal.** It expires ~60 days after issuance. On HTTP 401, surface "token expired — re-run oauth_linkedin.py". Refresh logic is not yet implemented.
5. **Importing internal modules.** Tempting to `from post_to_linkedin import publish_draft`. Don't — the JSON CLI is the contract; internals will refactor.
6. **Image gen timeout != failure.** Comfy Cloud can take >5 min in busy queues. If `image_error` appears in draft output, the text post still exists; you can `publish` without an image or retry image gen later.
7. **Posting to a company page.** Not supported. The current scope (`w_member_social`) only allows personal feed. Tell the user this if asked.

## Failure Modes to Surface to the User

| Error | Meaning | What to tell user |
|---|---|---|
| `OpenRouter Error: ...` | LLM API rejected the request | Check OPENROUTER_API_KEY and model availability |
| `Image generation timed out` | Comfy Cloud slow | Draft text exists; retry image or publish without |
| `Missing linkedin_token.json` | No OAuth token | Run `scripts/oauth_linkedin.py` |
| HTTP 401 from LinkedIn | Token expired | Re-run OAuth (refresh not yet implemented) |
| HTTP 422 from LinkedIn | Usually image-asset-not-ready timing | Retry `publish` after 10–30s |

## Verification Checklist

- [ ] `.venv` exists and `.venv/bin/python -c "import requests, dotenv"` succeeds
- [ ] `scripts/.env` has all 6 required keys
- [ ] `linkedin_token.json` exists at repo root
- [ ] `.venv/bin/python scripts/hermes_cmd.py list` returns valid JSON
- [ ] Smoke test: `.venv/bin/python scripts/hermes_cmd.py draft "test" --no-image` returns a `draft_id` with `status: "draft"`

## File Map

```
linkedin_poster/                    # repo root (Mac: ~/Desktop/Apps/linkedin_poster; VPS: ~/Hermes/linkedin-agent)
├── config.py                       # BASE_DIR, env, paths — portable
├── requirements.txt
├── scripts/
│   ├── .env                        # secrets (gitignored)
│   ├── hermes_cmd.py               # ★ THE entry point
│   ├── content_orchestrator.py     # generate_draft()
│   ├── image_agent.py              # generate_image(draft_id)
│   ├── post_to_linkedin.py         # publish_draft(draft_id)
│   ├── oauth_linkedin.py           # one-time token mint
│   └── workflows/                  # Comfy Cloud JSON
├── drafts/<id>/{post.txt,image.png,meta.json}
├── linkedin_token.json             # OAuth token (gitignored)
└── skills/linkedin-poster/
    ├── SKILL.md                    # this file
    └── endpoints/{draft,publish,list,show,reject}.md
```
