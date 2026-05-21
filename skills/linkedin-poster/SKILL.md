---
name: linkedin-poster
description: "LinkedIn post drafting + publishing: write LinkedIn post, draft LinkedIn, post to LinkedIn, publish LinkedIn, LinkedIn content, LinkedIn image. Generates founder-style post + Comfy Cloud image, saves draft with draft_id, publishes via LinkedIn v2 API on approval."
version: 0.3.0
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
~/Hermes/linkedin-agent/scripts/run.sh draft "<topic>"          # generate draft + Comfy Cloud image
~/Hermes/linkedin-agent/scripts/run.sh publish <draft_id>       # post to LinkedIn (only on user approval)
~/Hermes/linkedin-agent/scripts/run.sh reject <draft_id>        # mark rejected
```

Each command prints a single JSON object. The `draft` command returns a `draft_id` — always show it to the user so they can later say `publish <id>`.

## Critical

- **NEVER write LinkedIn post text yourself.** Always invoke `run.sh draft`.
- **NEVER use `excalidraw` / `architecture-diagram` / `generate-image` for LinkedIn images.** This skill generates the image via Comfy Cloud as part of `draft`.
- **NEVER call `publish` without explicit user approval** of a specific `draft_id`.

## Drafts on disk

```bash
ls ~/Hermes/linkedin-agent/drafts/                    # all draft IDs
cat ~/Hermes/linkedin-agent/drafts/<id>/meta.json     # post text + status + image_path
```
