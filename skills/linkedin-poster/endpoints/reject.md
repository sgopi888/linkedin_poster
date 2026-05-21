# reject — mark a draft as rejected

Soft-delete: the files stay on disk, but `meta.json.status` is set to `rejected` so it won't be published unless `publish --force` is used.

## Command

```bash
.venv/bin/python scripts/hermes_cmd.py reject <draft_id>
```

## Response

```json
{"draft_id": "20260520_212437", "status": "rejected"}
```

## Typical Hermes usage

Call when the user says "reject", "no", "trash this draft", "don't post that". Do not delete the files — keeping them allows audit + future "regenerate from rejected" workflows.
