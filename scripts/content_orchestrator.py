import os
import re
import sys
import json
import requests
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    draft_dir,
)


def _atomic_write(path: Path, content: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    tmp.replace(path)


def clean_linkedin_text(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    for pattern in [
        r"Here.?s your LinkedIn post.*?:",
        r"LinkedIn-ready post.*?:",
        r"crafted to align.*?:",
    ]:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = text.replace("---", "")
    for pattern in [
        r"This avoids hype.*",
        r"The pacing and structure.*",
        r"It highlights concrete.*",
    ]:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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


def _llm(prompt: str) -> str:
    """Prefer OpenAI direct (faster) when available; fall back to OpenRouter."""
    if OPENAI_API_KEY:
        return _openai_direct(prompt)
    return _openrouter(prompt)


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


WRITING_TEMPLATE = """
You are a technically credible AI infrastructure founder.

You think deeply about:
- agentic systems
- AI infrastructure
- long-term technological shifts
- memory systems
- human-AI interaction
- scalable intelligence architectures

Your writing style is:
- thoughtful
- calm
- systems-oriented
- technically grounded
- intellectually curious
- avoid unnecessary words
- every paragraph should contain a meaningful insight
- realistic instead of hype-driven

Write a highly engaging LinkedIn post.

WRITING GOAL:
The post should make technically literate readers pause and think.

Avoid generic futurism. Prefer concrete technical implications over abstract predictions.

STYLE:
- intelligent, technically grounded, visionary but realistic
- conversational, thoughtful, concise, human sounding, readable on mobile

AVOID:
- markdown, clickbait, hype language, emoji spam
- sounding AI-generated, motivational, or corporate

FORMATTING RULES:
- short paragraphs, clean whitespace
- use "-" for bullets, no numbered lists, no markdown syntax
- at most 3 tasteful hashtags at the end

IMPORTANT:
Return ONLY the final LinkedIn post. No intro like "Here is your LinkedIn post" or conclusion commentary.

USER REQUEST:
{user_prompt}

RESEARCH:
{research}
"""


def writing_agent(user_prompt, research):
    post = _llm(WRITING_TEMPLATE.format(user_prompt=user_prompt, research=research))
    return clean_linkedin_text(post)


def review_agent(post):
    issues = []
    for word in ["revolutionary", "game-changing", "unprecedented", "disruptive"]:
        if word.lower() in post.lower():
            issues.append(f"Hype term detected: {word}")
    if len(post) < 100:
        issues.append("Post too short.")
    if len(post) > 3000:
        issues.append("Post too long.")
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

    meta = {
        "draft_id": draft_id,
        "timestamp": draft_id,
        "user_prompt": user_prompt,
        "generated_post": post,
        "model": OPENAI_MODEL if OPENAI_API_KEY else OPENROUTER_MODEL,
        "provider": "openai-direct" if OPENAI_API_KEY else "openrouter",
        "review_issues": issues,
        "status": "rejected" if issues else "draft",
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
