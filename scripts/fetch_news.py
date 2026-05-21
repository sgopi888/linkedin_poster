import json
import requests
from datetime import datetime

NEWS_API_KEY = "YOUR_NEWSAPI_KEY"

url = (
    "https://newsapi.org/v2/everything?"
    "q=agentic AI OR generative AI OR LLM OR OpenAI"
    "&language=en"
    "&sortBy=publishedAt"
    "&pageSize=10"
)

headers = {
    "X-Api-Key": NEWS_API_KEY
}

response = requests.get(url, headers=headers)

data = response.json()

articles = []

for article in data.get("articles", []):

    articles.append({
        "title": article.get("title"),
        "description": article.get("description"),
        "url": article.get("url"),
        "source": article.get("source", {}).get("name"),
        "publishedAt": article.get("publishedAt")
    })

output = {
    "generated_at": datetime.utcnow().isoformat(),
    "articles": articles
}

with open("data/news.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"\nSaved {len(articles)} articles to data/news.json")