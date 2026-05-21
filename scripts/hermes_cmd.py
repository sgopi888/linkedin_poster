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
    if not args.no_image:
        # Default: gpt-image-1 stat card if topic looks stat-rich, else comfy mood.
        # Hermes can override with --image=comfy or --image=gpt-image and stat fields.
        backend = args.image
        if backend == "gpt-image":
            from openai_image import generate_image_openai
            try:
                img = generate_image_openai(
                    result["draft_id"],
                    headline=args.headline or args.topic[:60],
                    big_number=args.big_number or "",
                    caption=args.caption or "",
                )
                result["image_path"] = img["image_path"]
                result["image_backend"] = "gpt-image-1"
            except Exception as e:
                result["image_error_gpt"] = str(e)
                # fall back to comfy
                backend = "comfy"
        if backend == "comfy":
            try:
                img = generate_image(result["draft_id"])
                result["image_path"] = img["image_path"]
                result["image_backend"] = "comfy"
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


def cmd_regen_image(args):
    """Regenerate ONLY the image for an existing draft. No retrying the whole pipeline.

    Backends:
      comfy (default)    — mood / atmospheric image via Comfy Cloud (~30-60s)
      gpt-image          — editorial stat card via OpenAI gpt-image-1 (~15s, $0.04)
                           Requires --headline, --big-number, --caption.
    """
    _load_meta(args.draft_id)
    if args.backend == "gpt-image":
        from openai_image import generate_image_openai
        if not (args.headline and args.big_number and args.caption):
            _emit({"error": "gpt-image backend requires --headline, --big-number, --caption"}, 1)
        img = generate_image_openai(
            args.draft_id,
            headline=args.headline,
            big_number=args.big_number,
            caption=args.caption,
        )
    else:
        img = generate_image(args.draft_id)
    _emit({
        "draft_id": args.draft_id,
        "image_path": img["image_path"],
        "backend": img.get("provider", "comfy"),
        "regenerated": True,
    })


def main():
    p = argparse.ArgumentParser(prog="hermes_cmd")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("draft", help="Generate a new draft")
    sp.add_argument("topic")
    sp.add_argument("--no-image", action="store_true")
    sp.add_argument(
        "--image",
        choices=["gpt-image", "comfy"],
        default="gpt-image",
        help="Image backend. gpt-image (default): OpenAI stat card with accurate text. "
        "comfy: WAN mood image, no text.",
    )
    sp.add_argument("--headline", help="(gpt-image) headline at top of card; defaults to topic")
    sp.add_argument("--big-number", help="(gpt-image) hero stat in center, e.g. '$45B'")
    sp.add_argument("--caption", help="(gpt-image) source caption at bottom, e.g. 'Reuters, May 2026'")
    sp.add_argument(
        "--research",
        help="Pre-fetched research context (e.g., from Hermes' web tool).",
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

    sp = sub.add_parser("regen-image", help="Regenerate image for an existing draft")
    sp.add_argument("draft_id")
    sp.add_argument(
        "--backend",
        choices=["gpt-image", "comfy"],
        default="gpt-image",
        help="Image backend. gpt-image (default): stat card with text. comfy: mood image.",
    )
    sp.add_argument("--headline", help="(gpt-image) headline text")
    sp.add_argument("--big-number", help="(gpt-image) hero stat e.g. '$45B'")
    sp.add_argument("--caption", help="(gpt-image) source caption")
    sp.set_defaults(func=cmd_regen_image)

    args = p.parse_args()
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:
        _emit({"error": str(e), "type": type(e).__name__}, 1)


if __name__ == "__main__":
    main()
