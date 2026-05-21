import json
import requests

OPENROUTER_API_KEY = "YOUR_OPENROUTER_KEY"

with open("data/news.json", "r") as f:
    news_data = json.load(f)

top_articles = news_data["articles"][:5]

news_text = ""

for idx, article in enumerate(top_articles, start=1):

    news_text += f"""

    TITLE:
    {article['title']}

    DESCRIPTION:
    {article['description']}

    SOURCE:
    {article['source']}

    URL:
    {article['url']}

    """

    prompt = f"""
    You are an AI systems founder writing thoughtful LinkedIn posts.

    Write a highly engaging LinkedIn post based on the provided context.

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
    - hashtags
    - clickbait
    - hype language
    - emoji spam
    - sounding AI-generated

    FORMATTING RULES:
    - short paragraphs
    - clean whitespace
    - use "-" for bullets
    - no numbered lists
    - no markdown syntax
    - no "**"
    - no "*" bullets

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

    INPUT CONTEXT:

    {news_text}
    """


import re
import json
import requests

# =========================================
# LINKEDIN CLEANER
# =========================================

def clean_linkedin_text(text):

    # remove markdown bold
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)

    # remove markdown italic
    text = re.sub(r"\*(.*?)\*", r"\1", text)

    # remove hashtags
    text = re.sub(r"#\w+", "", text)

    # remove intro leakage
    bad_phrases = [
        "Here's your LinkedIn post:",
        "Here’s your LinkedIn post:",
        "In the style of",
        "LinkedIn-ready post:",
    ]

    for phrase in bad_phrases:
        text = text.replace(phrase, "")

    # normalize spacing
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()



response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "deepseek/deepseek-chat-v3-0324",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
)

result = response.json()

post_text = result["choices"][0]["message"]["content"]
post_text = clean_linkedin_text(post_text)

with open("drafts/linkedin_post.txt", "w") as f:
    f.write(post_text)

print("\nGenerated LinkedIn draft:\n")
print(post_text)