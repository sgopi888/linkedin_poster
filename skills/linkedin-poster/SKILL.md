---
name: linkedin
description: "LinkedIn post drafting + publishing (self-hosted, your OAuth, your Comfy Cloud image). Triggers on: draft LinkedIn, write LinkedIn, post to LinkedIn, publish LinkedIn, LinkedIn content, LinkedIn image, LinkedIn article. Generates founder-style post + image, saves draft with draft_id, publishes via LinkedIn v2 API on explicit user approval."
version: 0.4.0
author: sgopi888
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [linkedin, social-media, content-generation, comfy-cloud, publishing]
    related_skills: [xurl]
---

# linkedin-poster

ONE script does everything. Use it for any LinkedIn drafting / posting request.

```bash
# Generate draft + stat-card image (default: gpt-image-1 with accurate text rendering)
~/Hermes/linkedin-agent/scripts/run.sh draft "<topic with grounding facts>" \
    --headline "<key claim, e.g. Anthropic + SpaceX>" \
    --big-number "<hero stat, e.g. \$45B>" \
    --caption "<source, e.g. Reuters, May 2026>"

# Mood-only image (Comfy, no text in image, ~30-60s):
~/Hermes/linkedin-agent/scripts/run.sh draft "<topic>" --image comfy

# Regenerate image only (much faster than re-running the whole pipeline)
~/Hermes/linkedin-agent/scripts/run.sh regen-image <draft_id> \
    --headline "..." --big-number "..." --caption "..."

~/Hermes/linkedin-agent/scripts/run.sh publish <draft_id>   # only after user explicit approval
~/Hermes/linkedin-agent/scripts/run.sh reject <draft_id>
```

## Image backend (default: gpt-image-1)

- `gpt-image` (default, ~$0.04, ~15s): stat card with accurately rendered text. Use for news / funding / stats / company-name posts. Pass `--headline`, `--big-number`, `--caption`.
- `comfy` (~$0.01-0.05, ~30-60s, no text): pure mood image. Use when there's no clean stat to highlight, or the user explicitly asks for "no text" / "atmospheric".

When the user says "revise the image": use `regen-image <draft_id>`, NEVER re-run `draft` (that wastes a writer call). Re-use the same backend as the original by checking `drafts/<id>/meta.json` → `image_backend`, unless the user requested a backend change.

Each command prints a single JSON object. The `draft` command returns a `draft_id` — always show it to the user so they can later say `publish <id>`.

## Grounding — MANDATORY web search

Every LinkedIn post MUST be grounded in current web information. The writer model's training data is stale; using it alone produces outdated, sometimes incorrect posts.

**Required workflow**:

1. Call `web_search` with the topic + relevant year ("agentic memory systems 2026").
2. From the results, pick 3-5 concrete facts (titles, sources, dates, key claims).
3. Bake them into the topic string for `draft`, e.g.:
   ```bash
   ~/Hermes/linkedin-agent/scripts/run.sh draft "agentic memory systems — recent: [Paper X (arxiv 2026): finding 1]; [Company Y launched Z]; [Survey: 40% of agents now use ...]"
   ```
4. After `draft`, tell the user the sources you grounded the post in.

**Forbidden**:
- ❌ Calling `draft "<topic>"` with no grounding facts ever, unless `web_search` errored out AND you told the user "search failed, post is from model knowledge."
- ❌ Using `curl` / `python3` / `wget` for research — only `web_search` (it's free via Tavily/SerpAPI, no `tirith` prompts).
- ❌ Falling back to model knowledge silently. If web_search fails, say so out loud.

## Critical workflow rules — DO NOT VIOLATE

1. **NEVER write LinkedIn post text yourself.** Always invoke `run.sh draft`.

2. **NEVER use `excalidraw` / `architecture-diagram` / `generate-image` / `image_generate` (any other image tool) for LinkedIn images.** This skill owns image generation. Backends are `gpt-image-1` (primary) and `comfy` (fallback) — both AI. If both fail, surface the failure to the user. DO NOT improvise.

2b. **NEVER draw, render, or composite images with PIL / Pillow / ImageMagick / cairo / any Python or shell image library.** No text overlays, no caption layers, no manual rendering. Images come from the AI backends only. If text on the image is wrong, regenerate with a better prompt — do NOT paint over the result. If both AI backends fail, tell the user "both AI image backends failed" and stop. Do not write or install any image-drawing libraries.

3. **TWO SEPARATE TURNS for draft and publish.** After `run.sh draft` returns JSON:
   - Reply to the user with: the post text, the image, and the `draft_id`.
   - END YOUR REPLY. Do NOT run anything else.
   - Wait for the user to type literally `publish <draft_id>` or `approve <draft_id>` IN A NEW MESSAGE.
   - Only THEN invoke `run.sh publish <draft_id>`.

   It is a HARD VIOLATION to call `publish` in the same conversational turn as `draft`. The user has not seen the draft yet at that point. Even if the user originally said "draft and post", you still stop after draft and ask for confirmation.

4. **NEVER publish an old draft_id.** Always publish the draft you just created in the current turn. If multiple drafts exist, ask the user which `draft_id` to publish. Do not assume.

5. **ALWAYS surface the new draft to the user.** The Discord reply for a `draft` command must contain: full post text, image attachment (from `image_path`), and the literal `draft_id` string. Do not collapse, summarize, or skip these.

## Drafts on disk

```bash
ls ~/Hermes/linkedin-agent/drafts/                    # all draft IDs
cat ~/Hermes/linkedin-agent/drafts/<id>/meta.json     # post text + status + image_path + provider used
```

## Model chain (skill writer)

The skill writer tries models in this order (auto mode):
1. **gpt-5-nano** (OpenAI direct API, paid) — fast, primary. Counts toward 200/day cap.
2. **openrouter/auto** (free random model) — fallback when nano errors, or after the daily cap.

Empty completions or HTTP errors automatically advance to the next provider.

> Note: Hermes' main brain (your Discord conversation partner) is separately configured to use Codex via your ChatGPT subscription (free, not counted here). Only the skill's text-writing step uses this paid path because `hermes proxy` doesn't support `openai-codex` upstream.

User chat commands you should map to script calls:

| User says | Run |
|---|---|
| "model status" / "what model is the skill using" | `~/Hermes/linkedin-agent/venv/bin/python ~/Hermes/linkedin-agent/scripts/llm_budget.py status` |
| "force nano" | `... llm_budget.py set gpt-5-nano` |
| "force free" | `... llm_budget.py set free` |
| "auto model" / "reset choice" | `... llm_budget.py set auto` |
| "reset budget" / "reset counter" | `... llm_budget.py reset` |

Always show the JSON output to the user so they see what changed.
