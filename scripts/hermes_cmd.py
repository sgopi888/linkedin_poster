"""
Hermes-callable CLI for the LinkedIn pipeline.

All commands print a single JSON object to stdout on success.
Errors print {"error": "..."} with exit code 1.

Commands:
  draft "<topic>" [--no-image]   generate post (+image), save as new draft
  publish <draft_id> [--force]   publish a draft to LinkedIn
  reject <draft_id>              mark draft rejected

To inspect drafts, Hermes can read files directly:
  ls drafts/                       # all draft IDs
  cat drafts/<id>/meta.json        # one draft's status + post
"""
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import draft_dir  # noqa: E402
from content_orchestrator import generate_draft  # noqa: E402
from image_agent import generate_image  # noqa: E402
from post_to_linkedin import publish_draft  # noqa: E402


def _emit(obj: dict, code: int = 0):
    print(json.dumps(obj, indent=2))
    sys.exit(code)


def _load_meta(draft_id: str) -> dict:
    meta_path = draft_dir(draft_id) / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Unknown draft_id={draft_id}")
    return json.loads(meta_path.read_text())


def _save_meta_atomic(draft_id: str, meta: dict):
    """Atomic write: write to .tmp then rename. Prevents corruption on kill."""
    meta_path = draft_dir(draft_id) / "meta.json"
    tmp_path = meta_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(meta, indent=2))
    tmp_path.replace(meta_path)


def cmd_draft(args):
    research = args.research
    if args.research_file:
        research = Path(args.research_file).read_text()
    result = generate_draft(args.topic, research=research)
    if not args.no_image and not result["issues"]:
        try:
            img = generate_image(result["draft_id"])
            result["image_path"] = img["image_path"]
        except Exception as e:
            result["image_error"] = str(e)
    _emit(result)


def cmd_publish(args):
    meta = _load_meta(args.draft_id)
    if meta.get("status") == "posted":
        _emit({"draft_id": args.draft_id, "status": "already_posted"})
    if meta.get("status") == "rejected" and not args.force:
        _emit(
            {"error": f"draft_id={args.draft_id} is rejected. Use --force to publish anyway."},
            1,
        )
    _emit(publish_draft(args.draft_id))


def cmd_reject(args):
    meta = _load_meta(args.draft_id)
    meta["status"] = "rejected"
    _save_meta_atomic(args.draft_id, meta)
    _emit({"draft_id": args.draft_id, "status": "rejected"})


def main():
    p = argparse.ArgumentParser(prog="hermes_cmd")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("draft", help="Generate a new draft")
    sp.add_argument("topic")
    sp.add_argument("--no-image", action="store_true")
    sp.add_argument(
        "--research",
        help="Pre-fetched research context (e.g., from Hermes' web tool). "
        "If omitted, the skill runs its own OpenRouter research call.",
    )
    sp.add_argument(
        "--research-file",
        help="Path to a file containing research context (alternative to --research for long content).",
    )
    sp.set_defaults(func=cmd_draft)

    sp = sub.add_parser("publish", help="Publish a draft to LinkedIn")
    sp.add_argument("draft_id")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_publish)

    sp = sub.add_parser("reject", help="Mark a draft as rejected")
    sp.add_argument("draft_id")
    sp.set_defaults(func=cmd_reject)

    args = p.parse_args()
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:
        _emit({"error": str(e), "type": type(e).__name__}, 1)


if __name__ == "__main__":
    main()
