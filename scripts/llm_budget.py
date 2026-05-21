"""Daily-budget LLM router for the linkedin skill.

Default: openai/gpt-5-nano (direct OpenAI API, fast + cheap)
After DAILY_CAP calls: openrouter/free (random free model)
Manual overrides via state file at ~/.hermes/llm_budget.json

State schema:
    {
        "date": "YYYY-MM-DD",       # UTC day
        "calls_today": int,
        "override": null | "gpt-5-nano" | "free" | "auto"
    }
"""
import os
import json
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

BUDGET_FILE = Path(os.path.expanduser("~/.hermes/llm_budget.json"))
DAILY_CAP = 200

PROVIDERS = {
    "gpt-5-nano": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "auth_env": "OPENAI_API_KEY",
        "model": "gpt-5-nano",
        "extra_body": {"max_completion_tokens": 2000},
    },
    "free": {
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "auth_env": "OPENROUTER_API_KEY",
        "model": "openrouter/auto",  # routes to a free model
        "extra_body": {"max_tokens": 2000, "provider": {"data_collection": "allow"}},
    },
}


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_state() -> dict:
    if not BUDGET_FILE.exists():
        return {"date": _today_utc(), "calls_today": 0, "override": "auto"}
    try:
        s = json.loads(BUDGET_FILE.read_text())
    except Exception:
        s = {"date": _today_utc(), "calls_today": 0, "override": "auto"}
    if s.get("date") != _today_utc():
        s = {"date": _today_utc(), "calls_today": 0, "override": s.get("override", "auto")}
    return s


def _save_state(s: dict):
    BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = BUDGET_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(s, indent=2))
    tmp.replace(BUDGET_FILE)


def pick_provider() -> str:
    """Return 'gpt-5-nano' or 'free' based on override + budget."""
    s = _load_state()
    override = s.get("override", "auto")
    if override == "gpt-5-nano":
        return "gpt-5-nano"
    if override == "free":
        return "free"
    if s["calls_today"] >= DAILY_CAP:
        return "free"
    return "gpt-5-nano"


def call_llm(prompt: str) -> tuple[str, str]:
    """Call the chosen provider. Returns (response_text, provider_name).

    Increments the daily counter. Falls back to 'free' on provider error.
    """
    primary = pick_provider()
    for attempt_provider in (primary, "free"):
        cfg = PROVIDERS[attempt_provider]
        key = os.getenv(cfg["auth_env"])
        if not key:
            continue
        try:
            r = requests.post(
                cfg["endpoint"],
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": cfg["model"],
                    "messages": [{"role": "user", "content": prompt}],
                    **cfg["extra_body"],
                },
                timeout=60,
            )
            data = r.json()
            if "choices" not in data:
                raise RuntimeError(f"{attempt_provider}: {data.get('error', data)}")
            text = (data["choices"][0]["message"].get("content") or "").strip()
            if len(text) < 50:
                # Empty / near-empty completion — gpt-5-nano sometimes does this
                # on long prompts. Treat as failure so we fall back.
                raise RuntimeError(
                    f"{attempt_provider}: empty completion (len={len(text)})"
                )
            # Only count primary toward budget; fallback is free
            if attempt_provider == "gpt-5-nano":
                s = _load_state()
                s["calls_today"] += 1
                _save_state(s)
            return text, attempt_provider
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All providers failed. Last error: {last_err}")


# CLI for chat-driven status / override
if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if not args or args[0] == "status":
        s = _load_state()
        primary = pick_provider()
        out = {
            "date": s["date"],
            "calls_today": s["calls_today"],
            "daily_cap": DAILY_CAP,
            "override": s.get("override", "auto"),
            "current_provider": primary,
            "remaining": max(0, DAILY_CAP - s["calls_today"]),
        }
        print(json.dumps(out, indent=2))
    elif args[0] == "set" and len(args) == 2 and args[1] in ("auto", "gpt-5-nano", "free"):
        s = _load_state()
        s["override"] = args[1]
        _save_state(s)
        print(json.dumps({"override": s["override"]}, indent=2))
    elif args[0] == "reset":
        s = _load_state()
        s["calls_today"] = 0
        _save_state(s)
        print(json.dumps({"calls_today": 0, "reset": True}, indent=2))
    else:
        print(json.dumps({"error": "usage: llm_budget.py [status|set <auto|gpt-5-nano|free>|reset]"}, indent=2))
        sys.exit(1)
