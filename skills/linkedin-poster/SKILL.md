---
name: linkedin-poster
description: "LinkedIn post drafting + publishing: write LinkedIn post, draft LinkedIn, post to LinkedIn, publish LinkedIn, LinkedIn content, LinkedIn image, LinkedIn article. Generates founder-style post + Comfy Cloud image, saves as reviewable draft, publishes via LinkedIn v2 API on approval. Use for any LinkedIn posting task."
version: 0.2.0
author: sgopi888
license: MIT
platforms: [linux, macos]
prerequisites:
  commands: [bash]
metadata:
  hermes:
    tags: [linkedin, social-media, content-generation, ai-image, openrouter, comfy-cloud, founder-content, publishing]
    related_skills: [xurl]
---

# linkedin-poster

## Hard rules — read first

1. **For ANY LinkedIn content request, ALWAYS invoke the launcher.** Do not write LinkedIn post text in your reply directly. The launcher produces a tracked, persisted draft with a `draft_id`. Inline text is unreviewable, unsaved, and breaks the approval flow.

2. **For images, this skill uses Comfy Cloud** (`scripts/workflows/api_wan_text_to_image.json`) by default when running `draft`. NEVER use `excalidraw`, `architecture-diagram`, `generate-image`, or any other image skill for LinkedIn content. The image is generated as part of the `draft` command.

3. **Approval is explicit.** Never call `publish` unless the user said "publish <id>", "post <id>", "approve <id>", or similar with a specific `draft_id`.

4. **Always surface the `draft_id`** to the user from the JSON response so they can approve/reject it later.

## The launcher

ONE entry point, ONE absolute path. Works from any cwd:

```bash
~/Hermes/linkedin-agent/scripts/run.sh <command> [args]
```

The launcher script:
- `cd`s into the repo root
- Auto-detects venv (`.venv/` on Mac, `venv/` on VPS)
- Forwards args to `scripts/hermes_cmd.py`
- Prints a single JSON object to stdout

If the user's local repo is elsewhere, substitute the real path. On the production VPS the path above is correct.

## Commands

| Command | Purpose | Reference |
|---|---|---|
| `draft "<topic>" [--no-image]` | Generate post + Comfy Cloud image, save as new draft | `endpoints/draft.md` |
| `publish <draft_id> [--force]` | Post a draft to LinkedIn via v2 API | `endpoints/publish.md` |
| `reject <draft_id>` | Mark draft as rejected (soft-delete) | `endpoints/reject.md` |

To inspect drafts without invoking the CLI:

```bash
ls ~/Hermes/linkedin-agent/drafts/                       # list all draft IDs
cat ~/Hermes/linkedin-agent/drafts/<id>/meta.json        # one draft's status + post + image_path
```

**Load only the endpoint doc you need** when running that command. Each is small and self-contained.

## Typical Discord flow

```
User:    "draft a LinkedIn post about agentic memory"
You:     [run: ~/Hermes/linkedin-agent/scripts/run.sh draft "agentic memory"]
You:     [parse JSON → reply with post text + image attachment + draft_id]
You:     ["Approve with `approve <id>` or reject with `reject <id>`"]

User:    "approve 20260521_020000"
You:     [run: ~/Hermes/linkedin-agent/scripts/run.sh publish 20260521_020000]
You:     [reply "Posted ✅" or surface the error]
```

## Draft lifecycle

```
draft   ──► publish  ──► posted
       ╲                  
        ╲─► reject  ──► rejected   (files stay on disk; --force to publish anyway)
```

Drafts live at `~/Hermes/linkedin-agent/drafts/<draft_id>/{post.txt, image.png, meta.json}`. Status changes are persisted atomically in `meta.json`.

## Common pitfalls

1. **Forgetting the launcher.** Running `python scripts/hermes_cmd.py` directly with a system Python misses dependencies. Always use the launcher.
2. **Reaching for excalidraw / generate-image for LinkedIn images.** Don't. This skill owns the image step via Comfy Cloud.
3. **Auto-publishing.** Never run `publish` until the user explicitly approves with a specific `draft_id`. LinkedIn is the user's public brand.
4. **Loading all endpoint docs.** Only load `endpoints/<command>.md` for the command you're about to run.
5. **Treating the LinkedIn token as eternal.** It expires ~60 days. On HTTP 401, tell the user to re-run `oauth_linkedin.py`. (Refresh is implemented but only for tokens minted post-refactor.)
6. **Importing internal modules from Hermes.** The launcher / JSON contract is the only supported surface.

## Failure modes

| Error | Meaning | What to tell the user |
|---|---|---|
| `OpenRouter Error: ...` | LLM API rejected the request | Check OPENROUTER_API_KEY and model availability |
| `Image generation timed out` | Comfy Cloud slow | Draft text exists; retry image or publish without |
| `Missing linkedin_token.json` | No OAuth token | Run `~/Hermes/linkedin-agent/venv/bin/python scripts/oauth_linkedin.py` |
| HTTP 401 from LinkedIn | Token expired | Re-run OAuth |
| HTTP 422 from LinkedIn | Image-asset-not-ready timing | Retry `publish` after 10–30s |

## Installation (one-time)

The skill is symlinked into Hermes:

```bash
mkdir -p ~/.hermes/skills/social-media
ln -snf ~/Hermes/linkedin-agent/skills/linkedin-poster \
        ~/.hermes/skills/social-media/linkedin-poster
systemctl --user restart hermes-gateway.service
```

The repo needs a venv + .env + LinkedIn OAuth token:

```bash
cd ~/Hermes/linkedin-agent
python3 -m venv venv                 # or .venv — launcher auto-detects
venv/bin/pip install -r requirements.txt
# Create scripts/.env with the 6 keys (OPENROUTER_API_KEY, OPENROUTER_MODEL,
#   COMFY_CLOUD_API_KEY, LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET,
#   LINKEDIN_REDIRECT_URI)
venv/bin/python scripts/oauth_linkedin.py   # mints linkedin_token.json
```

## Verification checklist

- [ ] `~/Hermes/linkedin-agent/scripts/run.sh draft "test" --no-image` returns JSON with `draft_id` and `status: "draft"`
- [ ] `cat ~/Hermes/linkedin-agent/drafts/<id>/meta.json` shows the saved draft
- [ ] In Discord: "draft a LinkedIn post about X" causes Hermes to invoke this skill (not architecture-diagram, not excalidraw)
