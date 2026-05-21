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
~/Hermes/linkedin-agent/scripts/run.sh draft "<topic with grounding facts>"   # generate draft + Comfy Cloud image
~/Hermes/linkedin-agent/scripts/run.sh publish <draft_id>                     # post to LinkedIn (only on user approval)
~/Hermes/linkedin-agent/scripts/run.sh reject <draft_id>                      # mark rejected
```

Each command prints a single JSON object. The `draft` command returns a `draft_id` — always show it to the user so they can later say `publish <id>`.

## Grounding (default: try web search first)

Before calling `draft`, **try** to use your built-in `web` tool to gather 2-4 recent facts/sources about the topic. If `web` succeeds: bake the findings into the topic string you pass to `draft` (e.g., `draft "agentic memory systems — key 2026 findings: <fact1>; <fact2>; <fact3>"`). If `web` fails (rate limit, timeout, no results), proceed straight to `draft "<topic>"` with no findings — the post will be grounded in the writer model's knowledge instead.

**Rules**:
- Spend at most ~15 seconds on web research. If it stalls, move on.
- Do NOT use `curl` / `python3` ad-hoc — use the built-in `web` tool only (it skips `tirith` security prompts).
- After `draft`, tell the user explicitly whether the post is web-grounded or knowledge-only ("Web-grounded with 3 sources" vs "From model knowledge — web search timed out").

## Critical

- **NEVER write LinkedIn post text yourself.** Always invoke `run.sh draft`.
- **NEVER use `excalidraw` / `architecture-diagram` / `generate-image` for LinkedIn images.** This skill generates the image via Comfy Cloud as part of `draft`.
- **NEVER call `publish` without explicit user approval** of a specific `draft_id`.

## Drafts on disk

```bash
ls ~/Hermes/linkedin-agent/drafts/                    # all draft IDs
cat ~/Hermes/linkedin-agent/drafts/<id>/meta.json     # post text + status + image_path
```
