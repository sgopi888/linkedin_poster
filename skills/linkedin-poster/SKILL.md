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

## Model chain (Codex subscription → nano → free)

The skill tries models in this order (auto mode):
1. **Codex** (`gpt-5.5-codex` via your ChatGPT subscription, through `hermes proxy`) — free for you, primary path.
2. **gpt-5-nano** (OpenAI direct API, paid) — fallback if Codex unavailable. Counts toward 200/day cap.
3. **openrouter/auto** (free random model) — last resort, or when nano cap exhausted.

Empty completions or HTTP errors automatically advance to the next provider.

User chat commands you should map to script calls:

| User says | Run |
|---|---|
| "model status" / "what model" | `~/Hermes/linkedin-agent/venv/bin/python ~/Hermes/linkedin-agent/scripts/llm_budget.py status` |
| "force codex" / "use codex" | `... llm_budget.py set codex` |
| "force nano" | `... llm_budget.py set gpt-5-nano` |
| "force free" | `... llm_budget.py set free` |
| "auto model" / "reset choice" | `... llm_budget.py set auto` |
| "reset budget" / "reset counter" | `... llm_budget.py reset` |

Always show the JSON output to the user so they see what changed.
