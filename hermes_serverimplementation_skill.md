# Hermes Server Implementation — What Worked

Compiled from the end-to-end debugging session that got `/linkedin` posting live in Discord. Use this as the reproducible recipe for future skills on the same VPS.

---

## Final working architecture

```
Discord
  │
  ▼
Hermes gateway (systemctl --user hermes-gateway.service)
  │   brain: gpt-5.5 via openai-codex (ChatGPT subscription OAuth, free)
  │   web_search backend: tavily
  │   skills loaded from: ~/.hermes/skills/<category>/<name>/
  ▼
linkedin skill SKILL.md
  │
  ▼  via execute_code (terminal.backend: local)
~/Hermes/linkedin-agent/scripts/run.sh draft "<topic>"
  │
  ├─► content_orchestrator.py → llm_budget.py → OpenAI direct gpt-5-nano
  │     (max_completion_tokens: 8000 because nano is a reasoning model)
  │     fallback chain: gpt-5-nano (paid, 200/day cap) → openrouter/auto (free)
  │
  ├─► image_agent.py → Comfy Cloud (WAN text-to-image workflow)
  │
  └─► writes drafts/<draft_id>/{post.txt, image.png, meta.json}

User: "publish <draft_id>"
  ▼
post_to_linkedin.py → linkedin_auth.py → api.linkedin.com/v2/ugcPosts
```

---

## VPS layout

| Path | What it is |
|---|---|
| `~/.hermes/` | Hermes agent home (config, auth, skills, cron, gateway state) |
| `~/.hermes/config.yaml` | Hermes config — model, provider, web backend, toolsets |
| `~/.hermes/.env` | Hermes-level secrets (TAVILY_API_KEY, etc.) |
| `~/.hermes/auth.json` | OAuth credentials (openai-codex token) |
| `~/.hermes/skills/social-media/linkedin/` | The installed skill (REAL files, not symlink) |
| `~/.hermes/llm_budget.json` | Daily cap state for the skill writer |
| `~/Hermes/linkedin-agent/` | The app repo (cloned from GitHub) |
| `~/Hermes/linkedin-agent/venv/` | Repo venv (note: VPS uses `venv/`, Mac uses `.venv/`) |
| `~/Hermes/linkedin-agent/scripts/.env` | Skill-level secrets (OPENAI_API_KEY, COMFY, LinkedIn) |
| `~/Hermes/linkedin-agent/linkedin_token.json` | LinkedIn OAuth access token |

---

## Step-by-step recipe (what got us to working)

### 1. SSH access (one-time)

```bash
# ~/.ssh/config on Mac
Host hermes-vps
    HostName 159.198.76.206
    User sreekanth
    IdentityFile ~/.ssh/id_rsa_sgopi888
    IdentitiesOnly yes
```

Without `IdentitiesOnly yes` SSH offers wrong keys first and the server denies.

### 2. Skill must live inside `~/.hermes/skills/` — not as a symlink

**Failure mode**: symlinking the skill from the repo into `~/.hermes/skills/` produced this warning in gateway logs and made Hermes silently ignore the skill:

```
WARNING tools.skills_tool: Skill security warning for 'linkedin-poster':
skill file is outside the trusted skills directory (~/.hermes/skills/)
```

**Fix**: copy the real files in, sync from repo on each change:

```makefile
# Makefile
install-skill:
	mkdir -p ~/.hermes/skills/social-media
	rm -rf ~/.hermes/skills/social-media/linkedin
	cp -r skills/linkedin-poster ~/.hermes/skills/social-media/linkedin
```

### 3. Skill description must be short + keyword-dense for discovery

Long meta-instructional descriptions ("ALWAYS use this skill", "NEVER do X") **lose** the skill-ranking pass at session start because Hermes ranks by semantic match against `skills_list` metadata. The peer pattern (e.g. `xurl`) is one tight sentence packed with the trigger words. Behavioral rules go in the SKILL.md **body** (which only loads after the skill is picked).

Final description that worked:

```
LinkedIn post drafting + publishing (self-hosted, your OAuth, your Comfy Cloud image).
Triggers on: draft LinkedIn, write LinkedIn, post to LinkedIn, publish LinkedIn,
LinkedIn content, LinkedIn image, LinkedIn article. Generates founder-style post +
image, saves draft with draft_id, publishes via LinkedIn v2 API on explicit user approval.
```

### 4. Skill name should win lexical match — use a single keyword

Renaming `linkedin-poster` → `linkedin` was decisive. `linkedin-poster` was losing to `architecture-diagram` for any prompt mentioning "agentic" or "systems" because that word was in *that* skill's description. Single keyword `linkedin` makes it unbeatable for any LinkedIn-related prompt.

Also avoids collision with a third-party openclaw skill that's also named `linkedin-poster`.

### 5. Use a launcher script for path safety

Hermes (and users) regularly forgot to `cd` first. Wrapping all CLI access in one launcher at a stable absolute path with venv auto-detection fixed this permanently:

```bash
# scripts/run.sh
#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"
if   [[ -x ".venv/bin/python" ]]; then PY=".venv/bin/python"
elif [[ -x "venv/bin/python"  ]]; then PY="venv/bin/python"
else echo '{"error":"No venv found"}' >&2; exit 1
fi
exec "$PY" scripts/hermes_cmd.py "$@"
```

`scripts/hermes_cmd.py` is the JSON-in/out CLI. Skill body references **only** `~/Hermes/linkedin-agent/scripts/run.sh`.

### 6. `terminal.backend` and `web.backend` keys are different things

The fatal bug that caused 9-minute cron-thrashing was misunderstanding these keys in `~/.hermes/config.yaml`:

```yaml
# WRONG — empty string is not a valid terminal.backend value, blocks execute_code
terminal:
  backend: ''

# WRONG — 'tavily' is for search_backend, not terminal/sandbox backend
terminal:
  backend: tavily

# RIGHT
terminal:
  backend: local         # one of: local | docker | ssh | singularity | modal | daytona | vercel_sandbox

web:
  backend: ''             # auto-detect (Tavily picked up via TAVILY_API_KEY)
  search_backend: tavily
  extract_backend: tavily
```

Diagnostic symptom of `terminal.backend: ''`: Hermes' Discord agent fails `execute_code` with `ValueError: Unknown environment type` and falls back to creating cron jobs as a workaround to get a shell. If you see Hermes thrashing through `cronjob`/`delegate_task`/`skill_manage` for a simple shell command, this is the cause.

### 7. Web search needs both env keys AND backend config

```bash
# in ~/.hermes/.env
TAVILY_API_KEY=tvly-dev-...
SERPAPI_KEY=...           # optional; Tavily is preferred and natively supported

# in ~/.hermes/config.yaml
web:
  search_backend: tavily
  extract_backend: tavily
```

SerpAPI is NOT a native Hermes provider — only Tavily, Parallel, Firecrawl, Exa, SearXNG, Brave-free, DDGS. Set Tavily.

Without these, Hermes' Discord agent falls back to ad-hoc `curl ... | python3` which trips `tirith` security prompts every time.

### 8. Codex via ChatGPT subscription (free brain for Hermes)

Use ChatGPT-account OAuth instead of paid OpenAI API:

```bash
cd ~/.hermes/hermes-agent
./venv/bin/python -m hermes_cli.main auth add openai-codex --type oauth --no-browser
# Prints URL + device code; sign in via browser on another machine, paste code
```

Configure Hermes to use it:

```yaml
# ~/.hermes/config.yaml
model:
  default: gpt-5.5         # NOT gpt-5.5-codex — that needs API key, not OAuth
  provider: openai-codex
```

**Important**: `gpt-5.5-codex` returns HTTP 400 when authenticated via ChatGPT account. Supported models on OAuth: `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`.

Verify with:

```bash
./venv/bin/python -m hermes_cli.main status
# Look for: Model: gpt-5.5, Provider: OpenAI Codex, OpenAI Codex ✓ logged in
```

The dashboard UI may show empty for "default model" — cosmetic, ignore. The status command and the `Session reset!` banner in Discord are the authoritative sources.

### 9. Codex usage limits are NOT per-day token counts

ChatGPT Plus = baseline 1× Codex usage, resets on a 5-hour rolling window and weekly. You can't see a hard "messages/day" number — depends on prompt size. Use `/status` in Codex CLI for an estimate; Hermes doesn't expose this. Plan for fallback to gpt-5-nano when (not if) Codex returns a quota error.

### 10. Skill writer model: gpt-5-nano direct API with proper token budget

```bash
# scripts/.env
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-5-nano
OPENROUTER_API_KEY=sk-or-v1-...     # for free fallback
```

Critical: `max_completion_tokens` must be ≥ ~4000 for nano. Reason: nano is a reasoning model that spends 2000-2500 tokens on hidden reasoning before producing visible output. With `max_completion_tokens=2000`, all of it goes to reasoning and the visible response is **empty** with `finish_reason: "length"`. Use 8000 to be safe.

### 11. Daily budget + fallback chain

`scripts/llm_budget.py` implements:
- Default: `gpt-5-nano` direct (paid)
- After 200 calls in a UTC day: `openrouter/auto` (free)
- On any provider error / empty response: auto-advance to next
- State at `~/.hermes/llm_budget.json` (auto-resets at UTC midnight)
- CLI: `python llm_budget.py status | set <provider> | reset`

Counts only paid (gpt-5-nano) calls toward the cap; free overflow doesn't count.

### 12. Atomic writes for state files on a 24/7 VPS

Every script that writes `meta.json` or `linkedin_token.json` writes to `<path>.tmp` first then `os.rename()`. Without this, a SIGKILL mid-write corrupts state. We saw this happen with the gateway being killed during Discord interaction timeouts.

### 13. Gateway restart on this VPS: graceful shutdown often hangs

`systemctl --user restart hermes-gateway.service` regularly hangs in `deactivating | stop-sigterm` for 2+ minutes because of stuck Discord browser/web_extract tool calls. Workaround:

```bash
pid=$(systemctl --user show hermes-gateway.service --property=MainPID --value)
kill -9 $pid
sleep 5    # systemd auto-restart kicks in
systemctl --user is-active hermes-gateway.service  # should be 'active'
```

The `Discord connect timed out after 30s` log line during restart is normal — Discord gateway takes ~10-30s to reconnect.

### 14. Tirith security scanner (`~/.hermes/bin/tirith`)

Intercepts every shell command for URL/security analysis. Prompts for approval on `curl | python3` patterns and HTTP URLs. Two ways to reduce friction:

```yaml
# ~/.tirith/policy.yaml
allowlist:
  - "https://openrouter.ai/*"
  - "https://api.linkedin.com/*"
  - "https://www.linkedin.com/*"
  - "https://cloud.comfy.org/*"
  - "https://api.openai.com/*"
  - "https://api.tavily.com/*"
```

Better fix: make sure Hermes' brain uses the built-in `web_search`/`web_extract` tools (Tavily backend) instead of inventing `curl` calls — those go through Hermes' own networking and skip tirith entirely.

### 15. LinkedIn token: store with `issued_at` + `expires_at` from day one

```python
# scripts/oauth_linkedin.py
token_data["issued_at"] = int(time.time())
token_data["expires_at"] = token_data["issued_at"] + token_data.get("expires_in", 5184000)
```

`scripts/linkedin_auth.py` reads these to decide when to refresh. Tokens minted before this change have no expiry data and are treated as "valid until LinkedIn returns 401" — a re-OAuth upgrades them to the new format.

### 16. Per-ID draft directories prevent race conditions

```
drafts/<YYYYMMDD_HHMMSS>/
├── post.txt
├── image.png
└── meta.json   # status: draft | rejected | posted | post_failed
```

Two concurrent Discord requests would have overwritten `latest_post.txt` if we'd kept the old structure. Per-ID dirs make every draft independently addressable for `publish <id>` later.

---

## Reusable templates

### SKILL.md frontmatter that Hermes accepts

```yaml
---
name: <lowercase-hyphens-≤64>
description: "<keyword-dense one-sentence pitch, ≤1024 chars>"
version: 0.1.0
author: <you>
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [keyword, keyword, keyword]
    related_skills: [peer-skill-name]
---
```

### Add a new skill end-to-end on this VPS

```bash
# 1. Author in the repo (Mac)
mkdir -p skills/<name>
# write skills/<name>/SKILL.md  per template above
# (optional) endpoints/*.md for per-command refs

# 2. Add Makefile target
# install-skill-<name>: cp -r skills/<name> ~/.hermes/skills/<category>/<name>

# 3. Deploy
git add . && git commit -m "Add <name> skill" && git push

# 4. On VPS
ssh hermes-vps
cd ~/Hermes/linkedin-agent
git pull
make install-skill-<name>

# 5. Restart gateway (force-kill if graceful hangs)
pid=$(systemctl --user show hermes-gateway.service --property=MainPID --value)
kill -9 $pid; sleep 5

# 6. Verify in CLI
cd ~/.hermes/hermes-agent
./venv/bin/python -m hermes_cli.main skills list | grep <name>
# should show: │ <name> │ <category> │ local │ local │ enabled │
```

### Test the pipeline end-to-end without Discord

```bash
ssh hermes-vps
cd ~/Hermes/linkedin-agent

# 1. Skill smoke test (no image, no posting)
scripts/run.sh draft "test topic" --no-image
# expect: JSON with draft_id, post, status: "draft"

# 2. Check it appears in storage
cat drafts/<draft_id>/meta.json

# 3. Check model budget state
venv/bin/python scripts/llm_budget.py status

# 4. Hermes' view of the skill
cd ~/.hermes/hermes-agent
./venv/bin/python -m hermes_cli.main skills list | grep <name>
```

---

## Costs (current setup, May 2026)

| Component | Cost |
|---|---|
| Hermes brain (gpt-5.5 via Codex OAuth) | Included in ChatGPT subscription |
| Skill research + writer (gpt-5-nano direct, ~2 calls/draft × ~1500 input + 3000 output tokens) | ~$0.002/draft |
| Daily cap = 200 nano calls = ~100 drafts | ~$0.20/day worst case |
| Tavily web search | Free (1000/mo on dev tier) |
| Comfy Cloud image | ~$0.01-0.05/image (your account) |
| OpenRouter free fallback | $0 |
| LinkedIn API | Free |
| VPS (server2.neuroheart.ai) | Pre-existing |

Per fully-grounded post with image: ~$0.05 marginal cost.

---

## Common failure modes + fixes

| Symptom | Cause | Fix |
|---|---|---|
| `Skill security warning ... outside trusted skills directory` | Skill is a symlink into `~/.hermes/skills/` | Use `cp -r` (Makefile target) not `ln -s` |
| Discord: "There's no linkedin-poster skill available" | Skill loaded but ignored due to symlink warning | Same fix |
| 9 min cron-thrashing for a simple draft | `terminal.backend: ''` in config.yaml | Set to `local` |
| `ValueError: Unknown environment type: tavily` | `terminal.backend: tavily` (mistakenly set) | Set to `local` |
| Empty post returned, `finish_reason: "length"` | `max_completion_tokens` too low for nano reasoning | Raise to 8000+ |
| Hermes makes ad-hoc `curl arxiv` then hits `/approve` | `web_search` not auto-routing to Tavily | Set `TAVILY_API_KEY` in `~/.hermes/.env` + `search_backend: tavily` in config |
| HTTP 400 "'gpt-5.5-codex' not supported with ChatGPT account" | Used API-key-only model with OAuth | Use `gpt-5.5` (or `gpt-5.4`) |
| Hermes picks `architecture-diagram` instead of our skill | Skill description losing lexical match | Shorten description, rename skill to a single trigger keyword |
| Gateway restart hangs in `stop-sigterm` | Stuck Discord browser/web_extract call | `kill -9` the gateway pid; systemd auto-restarts in 5s |
| `Posted ✅` in Discord but no LinkedIn post | Token expired, returned 401 | `venv/bin/python scripts/oauth_linkedin.py` to re-mint |

---

## Codex quota + Hermes fallback chain (now configured)

When the ChatGPT subscription Codex quota is exhausted, Hermes flags the credential as `rate-limited (429)` with a countdown. The misleading user-facing error is **"No Codex credentials stored"** — credentials exist, they're just gated. `hermes auth list` shows the real status.

### Fix: fallback chain in `~/.hermes/config.yaml`

```yaml
fallback_providers:
  - provider: openrouter
    model: openai/gpt-5-nano       # paid, ~$0.001/msg, fast
  - provider: openrouter
    model: openrouter/auto         # free, last resort
```

### Manually reset a falsely-flagged rate-limit

```bash
cd ~/.hermes/hermes-agent
./venv/bin/python -m hermes_cli.main auth reset openai-codex
```

This doesn't restore actual quota — it only clears Hermes' local tracking. If you genuinely hit the 5h Codex cap, you wait it out (or fallback fires automatically with the config above).

## What still needs work (Phase 4)

- ~~Hermes fallback chain~~ (done — see above)
- Cron heartbeat for autonomous daily drafts (Hermes has built-in cron support; use `hermes cron`)
- Company-page posting (needs LinkedIn Advertising API approval)
- LinkedIn token refresh path (works for tokens minted post-refactor; old tokens still need manual re-OAuth)
- Pytest harness so the `hermes_cmd.py` JSON contract doesn't drift

---

## TL;DR — Six rules

1. **Skill files must be real (cp), not symlinked**, inside `~/.hermes/skills/<category>/<name>/`.
2. **Description is for discovery — short and keyword-dense**. Behavioral rules go in the body.
3. **`terminal.backend: local`** in `~/.hermes/config.yaml` (NOT `''`, NOT `tavily`).
4. **Tavily for web search**: `TAVILY_API_KEY` in `~/.hermes/.env` + `search_backend: tavily` in config.
5. **gpt-5.5 via openai-codex** for the brain (free with subscription); `max_completion_tokens: 8000` for any nano call.
6. **One launcher script** at a stable absolute path that handles `cd` + venv detection (`scripts/run.sh`).
