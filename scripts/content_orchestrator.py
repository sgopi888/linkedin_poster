import os
import re
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# =========================================
# LOAD ENV
# =========================================

load_dotenv(dotenv_path="/home/sreekanth/Hermes/linkedin-agent/.env")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("OPENROUTER_MODEL")

print("\n=== ACTIVE MODEL ===")
print(MODEL)

# =========================================
# USER INPUT
# =========================================

USER_PROMPT = " ".join(sys.argv[1:])

if not USER_PROMPT:
    raise Exception("No user prompt provided.")

# =========================================
# CLEANER
# =========================================

def clean_linkedin_text(text):

    import re

    # =========================================
    # REMOVE MARKDOWN BOLD
    # =========================================

    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)

    # =========================================
    # REMOVE MARKDOWN ITALIC
    # =========================================

    text = re.sub(r"\*(.*?)\*", r"\1", text)

    # =========================================
    # REMOVE LEAKED INTRO PHRASES
    # =========================================

    intro_patterns = [
        r"Here.?s your LinkedIn post.*?:",
        r"LinkedIn-ready post.*?:",
        r"crafted to align.*?:",
    ]

    for pattern in intro_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # =========================================
    # REMOVE --- SEPARATORS
    # =========================================

    text = text.replace("---", "")

    # =========================================
    # REMOVE META COMMENTARY
    # =========================================

    commentary_patterns = [
        r"This avoids hype.*",
        r"The pacing and structure.*",
        r"It highlights concrete.*",
    ]

    for pattern in commentary_patterns:
        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE | re.DOTALL
        )

    # =========================================
    # NORMALIZE SPACING
    # =========================================

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()

# =========================================
# RESEARCH AGENT
# =========================================

def research_agent(user_prompt):

    research_prompt = f"""
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
"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": research_prompt
                }
            ]
        }
    )

    result = response.json()

    print("\n=== RESEARCH RESPONSE ===\n")
    print(result)

    if "choices" not in result:
        raise Exception(f"OpenRouter Error: {result}")

    research = result["choices"][0]["message"]["content"]

    return research

# =========================================
# WRITING AGENT
# =========================================

def writing_agent(user_prompt, research):

    writing_prompt = f"""
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

You write like someone actively building and researching AI systems, not a social media creator.

Write a highly engaging LinkedIn post.

WRITING GOAL:
The post should make technically literate readers pause and think.

Avoid generic futurism.

Prefer concrete technical implications over abstract predictions.

Do not over-explain obvious concepts.

Assume the audience is not technically intelligent but common to any AI audience - tech and non tech but curious about AI.

STYLE:
- intelligent
- technically grounded
- visionary but realistic
- conversational
- thoughtful
- concise
- human sounding
- readable on mobile

AVOID:
- markdown
- clickbait
- hype language
- emoji spam
- sounding AI-generated
- sounding motivational
- corporate jargon

FORMATTING RULES:
- short paragraphs
- clean whitespace
- use "-" for bullets
- no numbered lists
- no markdown syntax
- no "**"
- no "*" bullets
- use at most 3 tasteful hashtags at the very end

GOOD STYLE EXAMPLE:

AI infrastructure is quietly changing.

The bottleneck is no longer compute alone.

Modern systems increasingly depend on:
- memory bandwidth
- orchestration
- distributed coordination

That changes how systems are designed.

END EXAMPLE.

IMPORTANT:
Return ONLY the final LinkedIn post.

The user input may include:
- AI news
- startup ideas
- projects
- GitHub repositories
- research papers
- technical thoughts
- product launches
- engineering work
- architecture discussions
- raw founder notes
- future predictions

Adapt naturally based on the user request.

Dont include any intro or conclusion like "Here is your linkedin post...", Here’s your LinkedIn post, nOr conclusion like "This avoids hype while..." etc;

INPUT CONTEXT:

USER REQUEST:
{user_prompt}

RESEARCH:
{research}
"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": writing_prompt
                }
            ]
        }
    )

    result = response.json()

    print("\n=== WRITING RESPONSE ===\n")
    print(result)

    if "choices" not in result:
        raise Exception(f"OpenRouter Error: {result}")

    post = result["choices"][0]["message"]["content"]

    post = clean_linkedin_text(post)

    return post

# =========================================
# REVIEW AGENT
# =========================================

def review_agent(post):

    issues = []

    banned_words = [
        "revolutionary",
        "game-changing",
        "unprecedented",
        "disruptive"
    ]

    for word in banned_words:
        if word.lower() in post.lower():
            issues.append(f"Hype term detected: {word}")

    if len(post) < 100:
        issues.append("Post too short.")

    if len(post) > 3000:
        issues.append("Post too long.")

    return issues

# =========================================
# MAIN ORCHESTRATOR
# =========================================

print("\n========================")
print("RESEARCHING...")
print("========================\n")

research = research_agent(USER_PROMPT)

print(research)

print("\n========================")
print("GENERATING POST...")
print("========================\n")

post = writing_agent(USER_PROMPT, research)

print(post)

print("\n========================")
print("REVIEWING...")
print("========================\n")

issues = review_agent(post)

if issues:

    print("POST REJECTED:\n")

    for issue in issues:
        print("-", issue)

else:

    print("POST APPROVED")
    # =========================================
    # SAVE POST
    # =========================================

    OUTPUT_POST = "/home/sreekanth/Hermes/linkedin-agent/drafts/latest_post.txt"

    with open(OUTPUT_POST, "w") as f:
        f.write(post)

    print(f"\nSaved post to: {OUTPUT_POST}")

    # =========================================
    # SAVE METADATA
    # =========================================

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    metadata = {
        "timestamp": timestamp,
        "user_prompt": USER_PROMPT,
        "generated_post": post,
        "model": MODEL,
        "status": "generated"
    }

    os.makedirs(
        "/home/sreekanth/Hermes/linkedin-agent/data/posts",
        exist_ok=True
    )

    metadata_path = (
        f"/home/sreekanth/Hermes/linkedin-agent/data/posts/"
        f"{timestamp}.json"
    )

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved metadata to: {metadata_path}")

print("\nDONE")