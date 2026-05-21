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
    # Codex via your ChatGPT subscription, exposed locally by `hermes proxy`.
    # No per-token cost; uses your OAuth login. Reasoning model — needs large
    # max_completion_tokens because gpt-5.5-codex spends most of its budget on
    # reasoning before emitting visible content.
    "codex": {
        "endpoint": os.getenv("CODEX_PROXY_URL", "http://127.0.0.1:8765/v1/chat/completions"),
        "auth_env": "CODEX_PROXY_KEY",  # any string; hermes proxy doesn't check it
        "model": os.getenv("CODEX_MODEL", "gpt-5.5-codex"),
        "extra_body": {"max_completion_tokens": 8000},
    },
    # Pay-per-token OpenAI direct — only used if CODEX_PROXY_URL unreachable.
    "gpt-5-nano": {
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "auth_env": "OPENAI_API_KEY",
        "model": "gpt-5-nano",
        "extra_body": {"max_completion_tokens": 8000},
    },
    # Last resort: free random model on OpenRouter.
    "free": {
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "auth_env": "OPENROUTER_API_KEY",
        "model": "openrouter/auto",
        "extra_body": {"max_tokens": 2000, "provider": {"data_collection": "allow"}},
    },
}

# Default fallback chain: try Codex first, then nano, then free.
DEFAULT_CHAIN = ["codex", "gpt-5-nano", "free"]


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


def pick_chain() -> list[str]:
    """Return the ordered fallback chain to try."""
    s = _load_state()
    override = s.get("override", "auto")
    # Manual pin to one provider — single-element chain
    if override in PROVIDERS:
        return [override]
    # Auto mode — try Codex first (free via subscription), then nano (paid),
    # then free OpenRouter. Skip nano if daily budget is exhausted.
    chain = ["codex"]
    if s["calls_today"] < DAILY_CAP:
        chain.append("gpt-5-nano")
    chain.append("free")
    return chain


# Backwards-compat: external callers may still ask for a single provider
def pick_provider() -> str:
    return pick_chain()[0]


def call_llm(prompt: str) -> tuple[str, str]:
    """Try providers in order. Returns (response_text, provider_name).

    - Codex (subscription, free) is tried first.
    - gpt-5-nano (paid OpenAI direct) is tried second, counts toward daily cap.
    - openrouter/auto (free) is the last resort.
    Empty / near-empty completions are treated as failures.
    """
    chain = pick_chain()
    last_err = None
    for attempt in chain:
        cfg = PROVIDERS[attempt]
        key = os.getenv(cfg["auth_env"], "" if attempt == "codex" else None)
        if key is None:
            continue  # no credential available for this provider
        try:
            r = requests.post(
                cfg["endpoint"],
                headers={
                    "Authorization": f"Bearer {key or 'sk-dummy'}",
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
                raise RuntimeError(f"{attempt}: {data.get('error', data)}")
            text = (data["choices"][0]["message"].get("content") or "").strip()
            if len(text) < 50:
                raise RuntimeError(f"{attempt}: empty completion (len={len(text)})")
            # Only paid providers count toward budget
            if attempt == "gpt-5-nano":
                s = _load_state()
                s["calls_today"] += 1
                _save_state(s)
            return text, attempt
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
        chain = pick_chain()
        out = {
            "date": s["date"],
            "calls_today": s["calls_today"],
            "daily_cap_paid_only": DAILY_CAP,
            "override": s.get("override", "auto"),
            "fallback_chain": chain,
            "remaining_paid_quota": max(0, DAILY_CAP - s["calls_today"]),
        }
        print(json.dumps(out, indent=2))
    elif args[0] == "set" and len(args) == 2 and args[1] in ("auto", "codex", "gpt-5-nano", "free"):
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
