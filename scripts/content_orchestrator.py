import os
import re
import sys
import json
import requests
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    draft_dir,
)
from llm_budget import call_llm  # noqa: E402


def _atomic_write(path: Path, content: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    tmp.replace(path)


# Humanizer scrub: words/phrases that scream "AI-written". From the
# linkedin-post-writer skill (kn78vd4zr956q020mrry482ath81gra0).
_BANNED_VOCAB = [
    "leverage", "utilize", "facilitate", "streamline", "robust", "seamless",
    "delve", "navigate", "unlock", "harness", "foster", "cultivate",
    "fundamentally", "essentially", "ultimately", "crucially", "notably",
    "landscape", "ecosystem", "paradigm", "realm", "tapestry", "journey",
    "revolutionary", "game-changing", "unprecedented", "disruptive",
    "needle-moving", "game-changer", "deep dive",
]

_BANNED_PHRASES = [
    r"in today.?s fast-paced world",
    r"it.?s not just .*?,? it.?s",
    r"at the end of the day",
]


def clean_linkedin_text(text):
    # markdown bold/italic
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    # leaked intros
    for pattern in [
        r"Here.?s your LinkedIn post.*?:",
        r"LinkedIn-ready post.*?:",
        r"crafted to align.*?:",
    ]:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = text.replace("---", "")
    # leaked outros
    for pattern in [
        r"This avoids hype.*",
        r"The pacing and structure.*",
        r"It highlights concrete.*",
    ]:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
    # em + en dashes → period or hyphen
    text = text.replace("—", ". ").replace("–", "-")
    # curly quotes → straight
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‘", "'").replace("’", "'")
    # banned phrases
    for pat in _BANNED_PHRASES:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    # collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def banned_vocab_hits(text: str) -> list[str]:
    """Return banned vocab words found in text (for review_agent issues)."""
    low = text.lower()
    return [w for w in _BANNED_VOCAB if re.search(rf"\b{re.escape(w)}\b", low)]


def _openai_direct(prompt: str) -> str:
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": 2000,
        },
        timeout=60,
    )
    result = r.json()
    if "choices" not in result:
        raise Exception(f"OpenAI Error: {result}")
    return result["choices"][0]["message"]["content"]


def _openrouter(prompt: str) -> str:
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": OPENROUTER_MODEL, "messages": [{"role": "user", "content": prompt}]},
        timeout=60,
    )
    result = r.json()
    if "choices" not in result:
        raise Exception(f"OpenRouter Error: {result}")
    return result["choices"][0]["message"]["content"]


_last_provider = "unknown"


def _llm(prompt: str) -> str:
    """Budget-aware LLM call. Default: gpt-5-nano. After 200/day: openrouter/free."""
    global _last_provider
    text, provider = call_llm(prompt)
    _last_provider = provider
    return text


def research_agent(user_prompt):
    return _llm(f"""
You are an elite AI research analyst.

Research the latest developments related to:

{user_prompt}

Return:
- top trends
- important companies
- technical shifts
- meaningful insights
- concise but informative analysis
- no hallucinations
""")


WRITING_TEMPLATE = """\
Write ONE LinkedIn post. Output the post text ONLY. No intro. No outro. No commentary.

VOICE
A technically credible AI infrastructure founder. Calm, specific, systems-oriented. Realistic, not hype-driven. Every paragraph carries a concrete insight.

2026 ALGORITHM RULES (these are non-negotiable)
- First line is the hook. Earn the "...see more" click in <=210 characters.
- Total length: 900-1,300 characters. Aim for the middle.
- Short paragraphs. Double line-break between ideas.
- 0-2 hashtags MAX, at the very end. Niche hashtags only. No more.
- No external URLs in the body.
- Hook → tension → 2-4 concrete points → reframe → close. No rule-of-three theatre.

PICK ONE HOOK FORMAT (do not name it in the output)
- Platform-risk anaphora: "[Platform] can [throttle] you. [Other platform] can [bad thing]." Stack 3-5 lines, then the reframe.
- R.I.P. category obituary: "R.I.P. [old thing]. Cause of death: [specific mechanism + number]."
- Time-anchor confession: "[N] months ago, I stopped [behavior]. Here is what happened."
- Year-over-year pivot: "In [last year], I [humble]. In [this year], I [transformational]. Here is what actually changed."
- Contrarian + historical receipts: "[Common belief] is wrong. The [decade ago] version of this story proves it."
- Curiosity-gap teaser: "[Surprising specific observation]. Here is what nobody is saying."

HARD CONSTRAINTS
- NEVER use em-dashes (—) or en-dashes (–). Use periods or hyphens.
- Vary sentence length aggressively. Mix 3-word sentences with 20-word sentences.
- Include at least one specific number, named entity, or concrete detail.
- One concrete vulnerability or real stake. Pure insight posts do not land in 2026.
- BANNED words (do not use): leverage, utilize, facilitate, streamline, robust, seamless, delve, navigate, unlock, harness, foster, cultivate, fundamentally, essentially, ultimately, crucially, notably, landscape, ecosystem, paradigm, realm, tapestry, journey, revolutionary, game-changing, unprecedented, disruptive, deep dive, game-changer, needle-moving.
- BANNED openers: "In today's fast-paced world", "It's not just X, it's Y", anything in all caps.
- No markdown. No "**bold**". No "*italic*". No ---.

TOPIC
{user_prompt}

RESEARCH (use specific facts, dates, names, numbers from this)
{research}
"""


def writing_agent(user_prompt, research):
    post = _llm(WRITING_TEMPLATE.format(user_prompt=user_prompt, research=research))
    return clean_linkedin_text(post)


def review_agent(post):
    """Check post against 2026 LinkedIn algorithm + humanizer rules.

    Returns soft warnings, not hard rejections. The writer's already
    constrained by WRITING_TEMPLATE; this is the safety net.
    """
    issues = []
    n = len(post)

    # Length: 900-1300 sweet spot. <400 / >1900 are real penalties.
    if n < 400:
        issues.append(f"Post too short ({n} chars; sweet spot 900-1300).")
    elif n > 1900:
        issues.append(f"Post too long ({n} chars; sweet spot 900-1300).")

    # Hook: first 210 chars must earn the "...see more" click
    first_line = post.split("\n", 1)[0]
    if len(first_line) > 210:
        issues.append(f"Hook line {len(first_line)} chars > 210 mobile cutoff.")
    if first_line.isupper():
        issues.append("All-caps hook — penalized.")

    # Em-dashes should be gone after clean_linkedin_text; if any survive, flag
    if "—" in post or "–" in post:
        issues.append("Em-dash or en-dash present (penalty signal).")

    # Banned vocab
    hits = banned_vocab_hits(post)
    if hits:
        issues.append(f"Banned vocab present: {', '.join(hits)}.")

    # Hashtags: 0-2 is current 2026 sweet spot; 5+ looks spammy
    hashtags = re.findall(r"#\w+", post)
    if len(hashtags) > 3:
        issues.append(f"{len(hashtags)} hashtags (>3); 0-2 is the 2026 sweet spot.")

    return issues


def generate_draft(user_prompt: str, research: str | None = None) -> dict:
    """Generate a draft. Returns dict with draft_id, post, issues, post_path, meta_path.

    If `research` is provided (e.g., pre-fetched by Hermes' free web tool), skip
    the paid OpenRouter research call and feed it straight to the writer.
    """
    if not user_prompt:
        raise ValueError("user_prompt is required")

    if research is None:
        research = research_agent(user_prompt)
    post = writing_agent(user_prompt, research)
    issues = review_agent(post)

    draft_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    ddir = draft_dir(draft_id)
    post_path = ddir / "post.txt"
    _atomic_write(post_path, post)

    # Hard rejection only for issues that genuinely tank a post.
    # Soft warnings (banned vocab, em-dashes, hashtag count) still let it
    # through as a draft so the user can review and decide.
    hard_keywords = ("Post too short", "Post too long", "All-caps hook", "Hook line")
    hard_failures = [i for i in issues if any(i.startswith(k) for k in hard_keywords)]

    meta = {
        "draft_id": draft_id,
        "timestamp": draft_id,
        "user_prompt": user_prompt,
        "generated_post": post,
        "provider": _last_provider,
        "review_issues": issues,
        "status": "rejected" if hard_failures else "draft",
        "research_source": "external" if research else "openrouter",
    }
    _atomic_write(ddir / "meta.json", json.dumps(meta, indent=2))

    return {
        "draft_id": draft_id,
        "post": post,
        "issues": issues,
        "post_path": str(post_path),
        "meta_path": str(ddir / "meta.json"),
        "status": meta["status"],
    }


if __name__ == "__main__":
    user_prompt = " ".join(sys.argv[1:])
    print(f"\nINPUT:\n{user_prompt}")
    result = generate_draft(user_prompt, research=None)
    print("\n=== POST ===\n")
    print(result["post"])
    if result["issues"]:
        print("\nISSUES:")
        for i in result["issues"]:
            print(" -", i)
    else:
        print(f"\nAPPROVED. draft_id={result['draft_id']}")
    print(f"\nSaved: {result['post_path']}")
