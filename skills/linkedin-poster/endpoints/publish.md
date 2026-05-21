# publish — post a draft to LinkedIn

Reads `drafts/<draft_id>/post.txt` and (if present) `image.png`, uploads to LinkedIn via the official `api.linkedin.com/v2/ugcPosts` endpoint, and updates `meta.json` with the result.

## Command

```bash
~/Hermes/linkedin-agent/scripts/run.sh publish <draft_id> [--force]
```

- `<draft_id>` — required. Format `YYYYMMDD_HHMMSS`. Use `list` to find it.
- `--force` — publish even if status is `rejected`. Default refuses.

## Response (success)

```json
{
  "draft_id": "20260520_212437",
  "status": "posted",
  "http_status": 201,
  "response": "{...LinkedIn ugcPost response...}"
}
```

## Response — already posted (no-op)

```json
{"draft_id": "...", "status": "already_posted"}
```

Idempotent — safe to retry.

## Response (failure)

Exit code 1:
- `{"error": "Unknown draft_id=..."}` — wrong ID.
- `{"error": "Missing linkedin_token.json..."}` — run `oauth_linkedin.py`.
- `status: "post_failed"` with `http_status: 401` — token expired.
- `status: "post_failed"` with `http_status: 422` — usually image-asset-not-ready timing; wait and retry.

## Visibility

Always posts to the **authenticated user's personal feed** as `PUBLIC`. Company-page posting requires the LinkedIn Advertising API product (not yet wired).

## Typical Hermes usage

Only call after the user explicitly approves a specific `draft_id`. Never publish autonomously without `--auto` flag from a trusted upstream (e.g., cron with `--from-news`).
