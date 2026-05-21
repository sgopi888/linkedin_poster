---
name: hermes-discipline
description: "Reflection and promotion discipline for this Hermes instance. Use when starting non-trivial multi-step work, after a failure or correction, when a workflow repeats, or when adding/changing rules in ~/.hermes/memories/. Enforces minimal retrieval, separated reflection vs promotion, hard promotion thresholds, protected rules, and 30-day expiration review. Prevents skill drift, garbage accumulation, runaway memory mutation."
version: 0.1.0
author: sgopi888
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [memory, discipline, reflection, promotion, governance, anti-drift]
    related_skills: [linkedin]
---

# hermes-discipline

How this Hermes instance learns without rotting.

## When to load

- Starting any multi-step task (>3 tool calls expected)
- After a failure, correction, or user "no, that's wrong"
- Before modifying anything in `~/.hermes/memories/`
- Before promoting a pattern to a memory or a skill
- During the monthly expiration review (1st of each month)

**Do not load** for trivial replies, casual chat, or one-shot factual answers.

## The Loop (six steps)

1. **Trigger** — non-trivial task, repeated workflow, failure, or long-running context.
2. **Retrieve** — read `~/.hermes/memories/MEMORY.md`. Then read AT MOST one extra support file (e.g. one skill SKILL.md). Do not load the full memory stack "just in case".
3. **Act** — execute the task. Do not narrate the loop unless the user asks.
4. **Reflect** — when work is done, compare intent vs outcome vs friction. If reusable, append ONE line to `~/.hermes/memories/REFLECTIONS.md` with date.
5. **Distill** — only if the lesson genuinely changes future execution, compress it into `~/.hermes/memories/MEMORY.md`.
6. **Promote** — only after the promotion threshold (below) is met, append to `~/.hermes/memories/PROMOTIONS.md` and recommend turning it into a dedicated skill.

## Promotion Threshold (HARD GATES)

Promote a pattern from reflection → memory → skill ONLY when:
- 3 successful uses in similar contexts, OR
- 2 failures followed by a stable fix, OR
- Explicit user request to institutionalize the behavior

Single events do not promote. Speculation does not promote.

## Good promotion candidates

- Consistent boot rituals for a project (e.g. always source `.venv` first)
- Repeated debugging workflows that worked
- Reliable review checklists used >=3 times
- Stable formatting / output preferences confirmed by the user
- Recurring post-task summary patterns the user thanked us for

## Bad promotion candidates (REJECT)

- One-off project hacks
- Temporary incidents
- Subjective style guesses without user confirmation
- Rules that only matter in one file or one hour
- "Nice ideas" with no usage evidence

## 🚨 Protected Rules (REQUIRE USER APPROVAL TO MODIFY)

These can NEVER be auto-modified, even with promotion threshold met. They require explicit user typed approval per change:

- Security boundaries (which tools can run shell, which APIs are whitelisted)
- Deletion policies (what files / drafts / memories can be removed automatically)
- Promotion thresholds (the 3-success / 2-fix rule above)
- Memory architecture (file structure under `~/.hermes/memories/`)
- Autonomous execution permissions (cron jobs, scheduled tasks)
- Provider / model selection rules (fallback chains, daily caps)
- Skill `SKILL.md` files (their frontmatter and core rules)

If user asks "improve our protected rules", you may DRAFT a proposal and show diff. Do not write the change until the user types approval.

## Expiration Review (every 30 days)

On or around the 1st of each calendar month, when this skill loads:

1. Scan `~/.hermes/memories/MEMORY.md` for entries older than 30 days.
2. For each: is it still true? Has the underlying tool/model/config changed?
3. Stale entries move to `~/.hermes/memories/archive/<YYYY-MM>.md`.
4. Report the review summary to the user — do not silently delete.

This prevents memory entropy growing forever.

## Anti-Drift Guardrails

- **No recursive self-modification**: this skill never edits itself or other skills' SKILL.md files. Only the user can.
- **Reflection ≠ promotion**: observations stay in REFLECTIONS.md until threshold proves they're rules. Don't shortcut.
- **One strong rule beats five similar notes**: when distilling, replace, don't append.
- **Quote evidence**: every memory line should be traceable to at least one concrete event. "I think the user prefers X" without a turn citation is speculation; flag for review.
- **No credentials / secrets / health / payment data** in memories — ever. If a memory would contain any, refuse and surface to user.

## File layout

```
~/.hermes/memories/
├── MEMORY.md           # HOT — active rules, ≤30 lines, read before non-trivial work
├── REFLECTIONS.md      # CHRONOLOGICAL — one line per significant work, with date
├── PROMOTIONS.md       # CANDIDATES — patterns with evidence count, awaiting threshold
└── archive/
    └── YYYY-MM.md      # Cold lessons, retired patterns, expired rules
```

Hermes already manages MEMORY.md natively. The other files we maintain manually via the loop.

## Status field (in MEMORY.md header, recommended)

| Value | Meaning | Behavior |
|---|---|---|
| `active` | full loop in use | reflect, distill, promote normally |
| `ongoing` | still calibrating user's preferred mode | adapt lightly |
| `paused` | user wants a temporary stop | read existing memory but don't expand |
| `archive-only` | read existing, don't write new | use existing rules, hold the line |

## TL;DR for the agent

When you see this skill loaded:
1. Read MEMORY.md (the hot file, short).
2. Do the work.
3. If something reusable happened, write ONE line to REFLECTIONS.md.
4. Only after 3 uses or explicit user ask, promote to MEMORY.md.
5. Never touch protected rules without typed user approval.
6. Monthly: archive stale entries (older than 30 days that no longer apply).
