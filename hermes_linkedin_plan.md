# Hermes ↔ LinkedIn Poster — Integration Plan

## Goal

User types in Discord → Hermes (on VPS) generates a draft → previews in Discord → user approves → Hermes publishes to LinkedIn. Same repo runs on Mac (dev) and VPS (prod).

```
Discord  ─►  Hermes Agent (VPS)  ─►  linkedin_poster skill
                  │                         │
                  └◄── JSON results ────────┘
                  │
                  ▼
              Discord (preview + approve/reject)
```

Discord message
↓
Hermes runtime
↓
linkedin-poster skill
↓
Generate post
↓
Generate image
↓
Approval
↓
LinkedIn API
↓
Posts to YOUR LinkedIn

## Current state (after refactor)

| Layer | Status |
|---|---|
| Self-hosted LinkedIn pipeline (OAuth + UGC posts via `api.linkedin.com`) | ✅ Working, no third-party |
| `hermes_cmd.py` single-entry CLI (draft / publish / list / show / reject) | ✅ JSON in/out, exit codes |
| Per-ID draft dirs (`drafts/<id>/`) | ✅ No race conditions |
| `config.py` portable paths (`BASE_DIR`) | ✅ Mac == VPS |
| Skill docs (`skills/linkedin-poster/SKILL.md` + per-endpoint `.md`) | ✅ Token-efficient layout |
| OpenRouter (DeepSeek) text generation | ✅ Tested locally |
| Comfy Cloud image generation | ⚠️ Untested locally (works on server) |
| LinkedIn posting | ⚠️ Untested locally (works on server) |
| Hermes skill loading on VPS | ❌ Unknown — needs SSH inspection |
| Discord ↔ Hermes ↔ skill round-trip | ❌ Not wired |
| LinkedIn token refresh | ❌ Token expires ~60 days, manual re-OAuth needed |
| Cron / autonomous mode | ❌ No scheduler yet |
| `fetch_news.py` topic source | ❌ Dead (placeholder API key) |
| Discord bot in this repo | n/a — owned by Hermes, not us |

## Gap analysis

### 1. Hermes integration unknown (BLOCKER for Discord flow)
We have a skill at `skills/linkedin-poster/`, but we don't yet know how Hermes discovers and invokes skills on the VPS. The old `skills/linkedin-api-1.0.7/` (Maton-based) suggested Hermes reads `SKILL.md` frontmatter, but unconfirmed.

**Action**: SSH to VPS, run `which hermes && hermes --help && ls ~/.hermes && find ~ -name "SKILL.md" 2>/dev/null`. Pick the discovery convention and conform.

### 2. Approval UX in Discord
Hermes currently chats but has no interactive components wired for our flow.

**Plan**: Text commands first — `approve <draft_id>` / `reject <draft_id>` parsed by Hermes, mapped to `hermes_cmd.py publish` / `reject`. Upgrade to Discord buttons later if Hermes' gateway supports them.

### 3. LinkedIn token lifecycle
`linkedin_token.json` is read raw; no expiry check, no refresh. Production breaks silently after ~60 days.

**Plan**: `scripts/linkedin_auth.py` with `get_access_token()` → checks `expires_at`, calls `/oauth/v2/accessToken` with `refresh_token` grant, rewrites file. All scripts import this instead of reading JSON.

### 4. No autonomous topic source
`fetch_news.py` exists but has `YOUR_NEWSAPI_KEY` placeholder and isn't wired.

**Plan**: Add real key to `scripts/.env`. Add `--from-news` flag to `hermes_cmd.py draft` that picks top unseen story (dedup against `data/posts/*.json`).

### 5. No scheduler
Nothing runs the pipeline on a cadence.

**Plan**: systemd timer on VPS:
```
ExecStart=/srv/linkedin_poster/.venv/bin/python scripts/hermes_cmd.py draft --from-news
```
Drops draft into queue; Hermes notices new draft and pings Discord for approval. (Or full auto-publish if user opts in.)

### 6. Image gen is slow + has no retry
`image_agent.py` polls Comfy every 5s, gives up at 10 min. No exponential backoff, no retry on 5xx.

**Plan**: Lower priority — works on server today. Add tenacity-style retry in v2.

### 7. Review layer is weak
Only banned-word + length check. No quality scoring, no topic relevance check, no image-text alignment check.

**Plan**: v2. Add an LLM-as-judge pass before marking draft `ready`.

### 8. No test coverage
Zero tests. Refactor was validated by one smoke run.

**Plan**: Pytest harness with mocked OpenRouter / Comfy / LinkedIn. Especially for `hermes_cmd.py` JSON contract — Hermes will break if the JSON shape changes.

### 9. `discord_bot.py` is a stub but README claims Discord integration
Confusing.

**Plan**: Delete `discord_bot.py`. Update README to say Discord is handled by Hermes, not this repo.

### 10. Other dead code
`scripts/generate_posts_unused.py`, `scripts/review_post.py` (duplicates orchestrator's review).

**Plan**: Delete both.

## Phased rollout

### Phase 1 — Foundation (DONE)
- [x] `config.py`, portable paths, `BASE_DIR`
- [x] Refactor `content_orchestrator.py`, `image_agent.py`, `post_to_linkedin.py` into importable functions
- [x] `scripts/hermes_cmd.py` — single CLI, JSON contract
- [x] Per-ID draft directories
- [x] `requirements.txt`, `.venv` ignored, `.env` ignored
- [x] `skills/linkedin-poster/` with per-endpoint docs
- [x] Drop Maton skill

### Phase 2 — VPS parity + Hermes wiring (NEXT)
- [ ] SSH to VPS, audit Hermes skill conventions
- [ ] `git pull` on VPS, smoke-test `hermes_cmd.py draft --no-image`
- [ ] Register `linkedin-poster` skill with Hermes (format TBD by audit)
- [ ] End-to-end test: Discord message → Hermes → `hermes_cmd.py draft` → reply with draft preview
- [ ] Wire `approve <id>` / `reject <id>` Discord text commands to `publish` / `reject`
- [ ] Delete `discord_bot.py`, `generate_posts_unused.py`, `review_post.py`. Update README.

### Phase 3 — Production hardening
- [ ] `scripts/linkedin_auth.py` with token refresh
- [ ] Pytest harness, mock the 3 external APIs
- [ ] Image gen retry + extended polling
- [ ] Add `--share-type article|article+thumbnail|image|video` (from LinkedIn tutorial transcript)

### Phase 4 — Autonomous mode
- [ ] Wire `fetch_news.py` with real key + dedup
- [ ] Add `--from-news` and `--auto` to `hermes_cmd.py draft`
- [ ] systemd timer on VPS for daily autonomous draft
- [ ] Optional: Discord buttons instead of text commands
- [ ] Optional: company-page posting (requires LinkedIn Advertising API approval)

## Findings from web research (Hermes + openclaw skill ecosystem)

### Confirmed facts (no longer guesswork)

- **Hermes runtime** = `NousResearch/hermes-agent` (confirmed via VPS audit: `~/.hermes/hermes-agent/`).
- **Skill format** = `SKILL.md` with YAML frontmatter, validated by `tools/skill_manager_tool.py` (name ≤64, description ≤1024, content ≤100k chars).
- **Discord slash commands are FREE.** Quote from docs: *"Any skill installed via `hermes skills install` is automatically registered as a Discord slash command on the next gateway restart."* We do not write a Discord bot. Hermes generates `/linkedin-poster` automatically.
- **Progressive disclosure / 3-level loading:**
  1. `skills_list()` — only metadata loaded at session start (~3k tokens for ALL skills combined).
  2. `skill_view(name)` — full `SKILL.md` loaded only when needed.
  3. `skill_view(name, path)` — single reference file (our `endpoints/*.md`) on demand.
  Our `endpoints/` split is already correct ✅.
- **Cron heartbeat is built into Hermes** (`~/.hermes/cron/`). No need for systemd timers for the autonomous mode.

### Peer skills worth referencing

- `~/.hermes/skills/social-media/xurl/SKILL.md` — official X/Twitter skill, our closest peer. We mirrored its structure ✅.
- [krnbwj/openclaw-skill-linkedin-poster](https://github.com/krnbwj/openclaw-skill-linkedin-poster) — OAuth-based LinkedIn poster. Has the **token refresh** flow we're missing. Pre-flight check → re-auth → save → continue.
- [openclaw/skills](https://github.com/openclaw/skills) — 13.7k community skills, including `arun-8687/linkedin-cli`.
- [jarvis-survives/openclaw-linkedin-skill](https://github.com/jarvis-survives/openclaw-linkedin-skill) — browser-control approach (more brittle, avoid).

### Stability + performance guidance from docs

> *"Keep skills narrowly scoped. Overly broad skills become too long and too vague."*

> *"Skills that aren't maintained become liabilities."*

> *"Update skills when they go stale. If you hit issues, tell Hermes to update the skill with what you learned."*

## Simplification / hardening pass (driven by research)

These supersede or refine Phase 2-3 items.

### Drop (less is more)

- [ ] Delete `scripts/run_pipeline.py` — Hermes won't call it; backward-compat for ourselves only and we don't need it.
- [ ] Delete `scripts/discord_bot.py`, `scripts/review_post.py`, `scripts/generate_posts_unused.py` — dead.
- [ ] **Drop `show` and `list` from `hermes_cmd.py`** — Hermes can `cat drafts/<id>/meta.json` and `ls drafts/` itself. Narrower skill = better. Document the file layout in SKILL.md instead.
- [ ] Remove the duplicate `data/posts/<id>.json` write in `content_orchestrator.py` — single source of truth is `drafts/<id>/meta.json`. Stops drift.

### Add (small, stability-focused)

- [ ] **Atomic `meta.json` writes**: write to `meta.json.tmp` → `os.rename()`. Prevents corruption on kill -9 / OOM mid-write on a 24/7 VPS.
- [ ] **`scripts/linkedin_auth.py`** — `get_access_token()` with expiry check + refresh-token grant. All scripts import it. Closes the silent 60-day failure.
- [ ] **Pre-flight check in SKILL.md "Setup"** so Hermes can self-diagnose: one command that prints `OK` if venv + .env + token are all present.
- [ ] **Symlink for install**: `ln -s ~/Hermes/linkedin-agent/skills/linkedin-poster ~/.hermes/skills/social-media/linkedin-poster` — one command, makes the skill discoverable to Hermes without forking out of the app repo. Document in SKILL.md.

### Leverage Hermes built-ins (don't rebuild)

- Use Hermes cron heartbeat (not systemd) for autonomous draft generation. Set up via `hermes` CLI; the cron config lives in `~/.hermes/cron/`.
- Use `hermes skills install` → automatic Discord slash command. Do not write a Discord bot.
- Use Hermes' built-in chat for approval flow — `/linkedin-poster draft "..."` → bot replies with preview → user replies in thread with `/linkedin-poster publish <id>`. No buttons, no router, no extra code.

## Updated Phase 2 (revised)

- [x] SSH to VPS, audit Hermes — DONE. It's `NousResearch/hermes-agent` at `~/.hermes/`.
- [x] Read Hermes' own skill-authoring guide on the VPS — DONE.
- [x] Update `SKILL.md` to match Hermes conventions (name, description ≤1024, version, license, prerequisites, hermes.tags) — DONE.
- [ ] Apply the **simplification / hardening pass** above (drop / add / leverage).
- [ ] `git push` from Mac, `git pull` on VPS.
- [ ] Symlink `linkedin-poster` skill into `~/.hermes/skills/social-media/`.
- [ ] Restart Hermes gateway. Confirm `/linkedin-poster` appears in Discord.
- [ ] End-to-end test in Discord: `/linkedin-poster draft "test"` → expect JSON preview reply.

## Open questions for you (reduced)

1. **Posting mode**: human-in-loop only, or also Hermes-cron autonomous? (Decides whether we add `--auto` + news source.)
2. **News source for autonomous**: NewsAPI / HN / arXiv RSS / custom? (Only matters if you said yes to autonomous.)
3. **Company page posting**: skip for now (default), or apply for LinkedIn Advertising API access?

(#4 from before — "what's the Hermes runtime" — is answered.)

## Sources

- [Hermes Agent — Skills feature docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
- [Hermes Agent — Working with Skills guide](https://hermes-agent.nousresearch.com/docs/guides/work-with-skills)
- [NousResearch/hermes-agent on GitHub](https://github.com/nousresearch/hermes-agent)
- [Hermes Discord integration docs](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/discord.md)
- [krnbwj/openclaw-skill-linkedin-poster](https://github.com/krnbwj/openclaw-skill-linkedin-poster) — OAuth + refresh reference
- [openclaw/skills registry](https://github.com/openclaw/skills) — `arun-8687/linkedin-cli` peer
- [VoltAgent/awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills) — 5400+ curated skills

## File map (post-refactor)

```
linkedin_poster/
├── config.py                       # paths + env, portable
├── requirements.txt
├── README.md
├── current_pipeline.md             # arch notes
├── hermes.md                       # vision doc
├── hermes_linkedin_plan.md         # THIS file
├── scripts/
│   ├── .env                        # gitignored — keys
│   ├── hermes_cmd.py               # ★ single CLI entry for Hermes
│   ├── content_orchestrator.py     # generate_draft()
│   ├── image_agent.py              # generate_image(draft_id)
│   ├── post_to_linkedin.py         # publish_draft(draft_id)
│   ├── oauth_linkedin.py           # one-time token mint
│   ├── run_pipeline.py             # backward-compat wrapper
│   ├── fetch_news.py               # TODO: wire + dedup
│   └── workflows/                  # Comfy Cloud JSON
├── skills/
│   └── linkedin-poster/
│       ├── SKILL.md                # index + setup + invariants
│       └── endpoints/
│           ├── draft.md
│           ├── publish.md
│           ├── list.md
│           ├── show.md
│           └── reject.md
├── drafts/<id>/                    # gitignored — per-draft files
│   ├── post.txt
│   ├── image.png
│   └── meta.json
├── data/posts/<id>.json            # gitignored — archive
└── images/<id>_<slug>.png          # gitignored — image archive
```
