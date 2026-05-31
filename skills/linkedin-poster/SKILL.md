## MANDATORY FIRST ACTION — read before doing anything else

On ANY drafting request ("draft a linkedin post", "write a linkedin post about X", "post about X", or any rewording), your FIRST tool call MUST be `~/Hermes/linkedin-agent/scripts/run.sh draft "<topic + grounding facts>"`. No exceptions.

**You are NOT a LinkedIn writer.** You are an orchestrator that calls `run.sh draft`. The script is the writer. You never compose post text in chat.

### Hard violations (each one is a failure, regardless of intent):

- Writing "Draft post text:" / "Draft LinkedIn post:" / "Here's a polished draft:" / "Post text (proposed):" in chat.
- Offering "Headline variant options", "Title options:", "Choose one:", or any list of title alternatives. You never pick titles — the writer does. ONE title, locked in.
- Pasting a `Sources:` list, "Practical checklist", "(1/2)" / "(2/2)" pagination, or any multi-part response with a draft inside.
- Asking "Would you like me to generate via run.sh draft?", "Want me to trigger the LinkedIn drafting workflow?", "Should I generate a draft_id-backed draft?", or any "Want me to…" / "Should I…" / "If yes, tell me…" question that delays calling the tool.
- Writing the post body in chat AND then offering to also run run.sh. There is no "also" — calling run.sh is the ONLY way to produce a draft.
- Surfacing an `image (attachment placeholder):` or Mint/article preview card as if it were the generated image. The only valid image is the one whose path `run.sh draft` returns in its JSON.

### The ONLY correct response shape for a drafting request:

1. Call `web_search` (if grounding is needed).
2. Pick `--headline`, `--big-number`, `--caption` from the grounded data (see "Image card argument discipline" below).
3. Call `~/Hermes/linkedin-agent/scripts/run.sh draft "<topic + grounding>" --headline "..." --big-number "..." --caption "..."`.
4. Read the returned JSON. Reply to Discord with EXACTLY THIS AND NOTHING ELSE:
   - the `post` field (the post body, verbatim)
   - the `image_path` as an attachment
   - one line: `Draft ID: <draft_id>`
   - one line: `Reply with "publish <draft_id>" to publish.`
5. STOP. Do NOT add: "What I did and why", "Would you like me to…", "Grounding sources", "Notes", "Further refine…", "(2/3) / (3/3)" pagination, or any explanation of your choices. The post body already contains the sources. The user can read it.

### Recency discipline (don't ship stale stats):

Your training data is months old. Real-world stats keep moving. Apply BEFORE drafting:

1. **Anchor on today's actual date.** Hermes injects today's date into context — use it. "This week", "this month", "H2 2026" are relative to TODAY, not to your training cutoff.

2. **Every web_search query MUST include a recency hint:**
   - Breaking news → query includes "this week" / "past 7 days".
   - Trend / forecast posts → query includes "last 90 days" or "Q2 2026" (or whichever quarter is current).
   - Open-source / GitHub spotlight → query includes "released this month".

3. **Discard stale results as headline material.** A result dated >90 days before today is NOT "recent" for a trend post, NOT "current" for a news post. Use it only as labeled baseline context ("Up from X in early 2025…").

4. **Forecast posts ("H2 2026", "predictions", "what's coming") require ≥1 stat from the last 60 days as the basis.** A forecast built only on year-old data is fabrication. If no recent stat exists, change the angle (don't force a forecast) or tell the user "couldn't find recent enough data — drafting as retrospective instead".

5. **Never call something "today's top AI story" if your most recent grounded source is >7 days old.** Be honest: "Most recent reporting available as of [today]: [stat]." Better than fake currency.

### Hermes-after-tool-call discipline (this is where you keep failing):

After `run.sh draft` returns, you are DONE drafting. Do not:
- Explain your reasoning ("I grounded the post in…", "I framed practical takeaways…").
- Offer refinements ("Further refine the post to embed 1–3 source links", "tailor the focus to…").
- Append a "Grounding sources" list — the post body already cites them inline.
- Add a "Notes" section with conditional offers ("If you want…, I can…").
- Break the reply into "(2/3)" / "(3/3)" pages.
- Ask any question. The next user message will tell you what to do; until then, wait.

The user wants ONE Discord reply: the post + image + draft_id + publish hint. That is THE END.

If you find yourself typing "What I did", "Would you like me to", "Grounding sources", "Notes", or "(N/M)" — STOP, delete it, and re-send just the post + image + draft_id.

### Image card argument discipline (for `--headline`, `--big-number`, `--caption`):

The `--big-number` you pass is rendered LITERALLY on the image. The card has no narrator. Three rules:

**1. `--big-number` MUST be a real stat that appears in the post body.**
Do NOT invent, round, or average numbers to fit a headline. If the post body's stats are "4.2%", "51%", "9x", "56%", "66%" — pick ONE of those for the card. Never a made-up `+134%` or `72%`.

**2. `--big-number` direction MUST match `--headline` direction.** Coherence check before submitting:
- Headline says "slowdown / decline / drop / cut / freeze / burn" → number must be a decrease, a negative, or a small/dropping figure.
- Headline says "surge / boom / growth / jump" → number must be increasing.
- Headline says "spent / cost / paid / blew" → number is the amount.
- BAD: headline "AI hiring bucks slowdown" + big_number "+134%". The headline says hiring fell, the number says it grew. Contradiction. Reject and rewrite.
- BAD: pre-pending `+` or `-` to a number to make it "feel" right. The post body's stat is the source of truth — copy it verbatim.

**3. `--caption` is a CONTEXT TAG, not a source citation.**
2 to 4 words. It says what the number measures. NEVER outlet+date.
- Good: big_number `51%` + caption `outside IT roles`. big_number `$500M` + caption `in 30 days`. big_number `21,459` + caption `GitHub stars`.
- BAD: caption `Lightcast May 2025`, `Indeed Jan 2026`, `Reuters, May 27 2026`. The post body cites sources; the card does NOT.
- BAD: caption `Grounded by the latest data` or `Multiple sources`. That's filler. Reject.

**4. Format the number string itself per AGENT_PROMPT.md rules**: uppercase suffixes (`10K`, `1.7M`, `45B`), `$` for money, `%` for percentages, `x` for multipliers. Never lowercase `m`/`k`/`b`. Max 6 chars including symbol.

**5. If you can't satisfy 1+2+3 cleanly, switch to `--image comfy` for a mood image.** A meaningless or contradictory stat card hurts more than no stat card.

The `--headline` (3-6 words) is the question; `--big-number` is the answer; `--caption` is the unit. All three together must form one coherent thought.

---

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

- `gpt-image` (default, ~$0.04, ~15s): stat card with accurately rendered text. Use for news / funding / stats / company-name posts. Pass `--headline`, `--big-number`, `--caption`. For breaking-news/investment posts, put exactly one shocking stat in the headline/opening hook (e.g. “Breaking News: Anthropic makes $45B deal for SpaceX compute”) and keep wording understandable to non-technical readers. Do not cram multiple stats into the first line. Keep the current content density and size, but deliberately vary colors, layout, background, and visual theme across drafts so cards do not all look similar.
- `comfy` (~$0.01-0.05, ~30-60s, no text): pure mood image. Use when there's no clean stat to highlight, or the user explicitly asks for "no text" / "atmospheric".

When the user says "revise the image": use `regen-image <draft_id>`, NEVER re-run `draft` (that wastes a writer call). Re-use the same backend as the original by checking `drafts/<id>/meta.json` → `image_backend`, unless the user requested a backend change.

Image variation is a standing quality requirement: Sreekanth likes the current LinkedIn card content density and square size, but future images should vary color palette, visual theme, composition, and background treatment so they do not all look like the same dark stat-card template. If `gpt-image-1` is blocked on a sensitive/political current-events prompt, retry with neutral/non-political image words where possible; otherwise use the skill fallback (`comfy`) and clearly surface that the image is mood/visual-only rather than a text stat-card.

For politically sensitive news requests where Sreekanth says not to mention a person or party, enforce that constraint in the generated post, image headline/caption arguments, hashtags, and delivered response. Verify with a case-insensitive text check before showing the draft. See `references/current-events-style.md` for examples from prior sessions.

Each command prints a single JSON object. The `draft` command returns a `draft_id` — always show it to the user so they can later say `publish <id>`.

## Grounding — MANDATORY web search

Every LinkedIn post MUST be grounded in current web information. The writer model's training data is stale; using it alone produces outdated, sometimes incorrect posts.

For breaking-news posts, use items from the last 1 day whenever possible; worst case, use only items from the last 1 week. Do not present older announcements as current breaking news. Older items may appear only as explicitly labeled background/context, not as the headline.

For LinkedIn posts, add tasteful emojis to the header/opening line and top sentences. Keep them professional and sparse; do not overload the post.

For daily AI news selection, search broadly for hot/trending AI news, not only investment news. Pick exactly ONE top trending/highest-signal news item and build the post around that single story. Do not create roundups or lists of multiple news items unless the user explicitly asks for a roundup. Prefer stories with visible attention signals when discoverable (major outlets, social posts with high views/engagement, repeated coverage across sources). Before drafting, check `/home/sreekanth/Hermes/linkedin-agent/MEMORY.md` and recent `drafts/*/meta.json` to avoid duplicating a topic already drafted or published. After drafting/posting, update MEMORY.md with 1–2 concise lines: topic, status, and avoid-repeat note.

For open-source AI tooling posts, pick exactly ONE recent open-source AI/LLM/agentic tool release or major update. Rank candidates by recency plus GitHub stars/forks and practical relevance. Use GitHub/search evidence for repo stars/forks and release date when creating a new draft. Do not repeat tools/topics already in MEMORY.md or recent drafts. Frame the post around why the tool matters to builders, not a generic list of tools.

Open-source spotlight style for Sreekanth:
- Pick tools by **recency + GitHub stars/forks + practical relevance**. If comparing candidates, prefer the most recent high-star project unless another tool has clearly stronger builder value.
- Tile/title should be short and explicit: tool name + what it does + GitHub stars/social proof. Prefer “OpenViking: AI Agent Memory + Skills Management — 24,550 GitHub Stars” over vague titles like “OpenViking has 24,550 GitHub stars.”
- Body copy should be concise, not essay-like. Use actual bullets (`•`) when the user asks for bullets; do not fake bullets with long paragraph sections.
- Bullets must flow as a natural storyline, not blunt Q&A labels. Avoid headings like “Why it matters / Why choose it / How to use it safely” unless the user explicitly asks for that format.
- For developer-reader posts, do **not** dwell on publication time, pushed dates, release timestamps, or version minutiae. The reader cares why to use the tool: transparency, model/provider flexibility, terminal/desktop/IDE UX, privacy/compliance, community velocity, and workflow leverage.
- Add only enough alternatives context to clarify why this tool is unique; do not overdo comparison lists. If the user asks for one-line context, use a single middle sentence comparing against alternatives, then continue the main bullet flow. Example: “Unlike Aider, Open Interpreter, and OpenHands, OpenCode is a terminal-first, IDE-like agent focused on fast, interactive coding sessions with LSP-powered intelligence and multiple running agents in one project.”
- Lead with practical builder value: what the tool enables, why it matters, and how developers can safely adopt it.
- Include adoption guardrails when relevant: repo permissions, sandboxing, diff review, tests, and human approval.
- Avoid overloading the post with release-note minutiae unless the user asks for deeper technical detail.

Example title pattern: “Promptfoo: AI evals + red-teaming — 21,459 GitHub stars.”
Example bullet-story flow: infrastructure shift → open-source transparency → model/provider choice → multi-platform workflow → privacy/compliance → safe adoption guardrails.

**Required workflow**:

1. Call `web_search` with the topic + relevant year ("agentic memory systems 2026").
2. From the results, pick 3-5 concrete facts (titles, sources, dates, key claims).
3. Bake them into the topic string for `draft`, e.g.:
   ```bash
   ~/Hermes/linkedin-agent/scripts/run.sh draft "agentic memory systems — recent: [Paper X (arxiv 2026): finding 1]; [Company Y launched Z]; [Survey: 40% of agents now use ...]"
   ```
4. After `draft`, tell the user the sources you grounded the post in, including 1-3 source links.

Citation-link rule for Sreekanth:
- The LinkedIn post/draft itself should include 1–3 concise citation/source links whenever practical, usually under a short `Sources:` section at the end.
- Do not only mention sources in the assistant's final response; the post body should carry the links so the published post is self-verifiable.
- Avoid date-heavy source prefixes unless needed for clarity.

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

6. **When the user approves a previously shown draft/image and asks to post it, do not regenerate or re-research by default.** Locate the existing draft, apply only the requested text edits to `post.txt`/`meta.json`, verify `image.png` exists, then run `publish <draft_id>`. Only re-run search/draft/image generation if the user explicitly asks for fresh research or a new image, or if the existing draft/image cannot be found.

7. **For scheduled publishing of an approved draft, preserve the existing image.** If the user says “cron it,” “schedule it,” or “post later,” create a one-shot cron job that publishes the existing `draft_id` without browsing/regenerating. The cron prompt must explicitly verify both `post.txt` and `image.png` and state that `run.sh publish <draft_id>` should publish an IMAGE post, not text-only.

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

Always show the JSON output to the user so they see what changed.\n\nExtended guidance and grounding updates (2026-05):\n- Ground LinkedIn posts in web search results; require 1-3 citations embedded in the post body.\n- Use the run.sh draft workflow exclusively; never manually type post text for public posting.\n- Image generation must use the designated image backends (gpt-image-1 or comfy); avoid local image composition or text overlays.\n- Drafts must include a draft_id; publish only after explicit user confirmation (publish <draft_id>).\n- Maintain a calm, technically grounded tone; avoid hype and overpromising.\n- Include a concise Sources section with 1-3 links at the end of the draft.
