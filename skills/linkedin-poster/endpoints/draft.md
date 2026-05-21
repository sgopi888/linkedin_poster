# draft — generate a new LinkedIn post

Generates a founder-style post via OpenRouter, runs a hype-word/length review, and (by default) generates an image via Comfy Cloud. Saves to `drafts/<draft_id>/`.

## Command

```bash
~/Hermes/linkedin-agent/scripts/run.sh draft "<topic>" [--no-image]
```

- `<topic>` — required. Free-text topic. Wrap in quotes.
- `--no-image` — skip image generation (faster, cheaper; text only).

## Response (success)

```json
{
  "draft_id": "20260520_212437",
  "post": "The quiet revolution in edge AI...",
  "issues": [],
  "post_path": "/abs/path/drafts/20260520_212437/post.txt",
  "meta_path": "/abs/path/drafts/20260520_212437/meta.json",
  "status": "draft",
  "image_path": "/abs/path/drafts/20260520_212437/image.png"
}
```

- `status: "draft"` → ready for review/publish.
- `status: "rejected"` → review_agent flagged hype words / length. See `issues`.
- `image_path` is absent if `--no-image` or if image generation failed (then `image_error` is set).

## Response (failure)

Exit code 1, stdout:

```json
{"error": "OpenRouter Error: ...", "type": "Exception"}
```

## Cost

- OpenRouter (research + writing): ~$0.0005 per draft (DeepSeek v3).
- Comfy Cloud image: depends on workflow; typically ~$0.01–0.05.

## Typical Hermes usage

1. Run `draft "topic"`.
2. Parse JSON. If `issues` is non-empty, surface them to the user; don't auto-publish.
3. Reply in Discord: post text + image attachment + `draft_id`.
4. Wait for user `approve <id>` or `reject <id>`.
