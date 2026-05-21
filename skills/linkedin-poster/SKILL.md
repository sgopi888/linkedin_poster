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

## Critical

- **NEVER write LinkedIn post text yourself.** Always invoke `run.sh draft`.
- **NEVER use `excalidraw` / `architecture-diagram` / `generate-image` for LinkedIn images.** This skill generates the image via Comfy Cloud as part of `draft`.
- **NEVER call `publish` without explicit user approval** of a specific `draft_id`.

## Drafts on disk

```bash
ls ~/Hermes/linkedin-agent/drafts/                    # all draft IDs
cat ~/Hermes/linkedin-agent/drafts/<id>/meta.json     # post text + status + image_path + provider used
```

## Model budget (gpt-5-nano with 200/day cap, then openrouter/free)

The skill uses **gpt-5-nano direct** by default (~1.7s, cheap). After 200 calls in a UTC day, it auto-falls-back to **openrouter/free** (random free model). Counter resets at UTC midnight.

User chat commands that you should map to script calls:

| User says | Run |
|---|---|
| "model status" / "what model" / "model usage" | `~/Hermes/linkedin-agent/venv/bin/python ~/Hermes/linkedin-agent/scripts/llm_budget.py status` |
| "force gpt-5-nano" / "use nano always" | `... llm_budget.py set gpt-5-nano` |
| "force free model" / "switch to free" | `... llm_budget.py set free` |
| "auto model" / "reset model choice" | `... llm_budget.py set auto` |
| "reset model counter" / "reset budget" | `... llm_budget.py reset` |

Always show the JSON output to the user so they see what changed.
