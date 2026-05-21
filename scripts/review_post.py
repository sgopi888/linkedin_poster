import re

with open("drafts/linkedin_post.txt", "r") as f:
    post = f.read()

issues = []

# Too long
if len(post) > 3000:
    issues.append("Post exceeds LinkedIn length comfort zone.")

# Too many hashtags
hashtags = re.findall(r"#\w+", post)

if len(hashtags) > 5:
    issues.append("Too many hashtags.")

# Hype words
banned_words = [
    "revolutionary",
    "game-changing",
    "unprecedented",
    "disruptive"
]

for word in banned_words:
    if word.lower() in post.lower():
        issues.append(f"Hype term detected: {word}")

# Empty
if len(post.strip()) < 50:
    issues.append("Post too short.")

print("\n=== REVIEW REPORT ===\n")

if issues:
    for issue in issues:
        print(f"- {issue}")

    print("\nPost needs review.")

else:
    print("Post approved.")