"""Report Claude Code token usage for this repo's sessions (read-only).

Every API call re-sends the whole conversation, so the number that drives
usage is context size per call, not file count. This parses the session
transcripts Claude Code keeps under ~/.claude/projects/<repo-slug>/ and
prints, per session: API calls, cached tokens re-read, average and peak
context, output tokens, images read, compactions, the most re-read files
and the largest tool results.

    python scripts/token_report.py              # 5 most recent sessions
    python scripts/token_report.py --last 10
    python scripts/token_report.py <session-id-prefix> [...]

Targets (AGENT_GUIDE.md -> "Context Budget"): average context per call
under ~150k and peak under ~250k. Run one stage per session (/next-stage).
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def transcripts_dir() -> Path:
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(ROOT))
    base = Path.home() / ".claude" / "projects"
    for candidate in (slug, slug[0].lower() + slug[1:], slug[0].upper() + slug[1:]):
        if (base / candidate).is_dir():
            return base / candidate
    return base / slug


def _k(n: float) -> str:
    if n >= 1e9:
        return f"{n / 1e9:.2f}B"
    if n >= 1e6:
        return f"{n / 1e6:.1f}M"
    if n >= 1e3:
        return f"{n / 1e3:.0f}k"
    return str(int(n))


def analyse(path: Path, top: int) -> dict:
    usage: dict[str, dict] = {}  # one API response is logged as several entries sharing message.id
    models: Counter = Counter()
    reads: Counter = Counter()
    tool_names: dict[str, tuple[str, str]] = {}
    results: list[tuple[int, str, str]] = []
    images = compactions = 0

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") == "system" and entry.get("subtype") == "compact_boundary":
                compactions += 1
            msg = entry.get("message") or {}
            if entry.get("type") == "assistant" and msg.get("usage"):
                key = msg.get("id") or entry.get("uuid")
                if key not in usage:
                    models[msg.get("model")] += 1
                usage[key] = msg["usage"]
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    inp = block.get("input") or {}
                    target = inp.get("file_path") or inp.get("command") or inp.get("pattern") or ""
                    tool_names[block.get("id")] = (block.get("name", "?"), str(target))
                    if block.get("name") == "Read" and inp.get("file_path"):
                        reads[os.path.basename(inp["file_path"])] += 1
                elif block.get("type") == "tool_result":
                    body = block.get("content")
                    if isinstance(body, list):
                        if any(isinstance(b, dict) and b.get("type") == "image" for b in body):
                            images += 1
                            continue
                        text = "".join(b.get("text", "") for b in body if isinstance(b, dict))
                    else:
                        text = str(body or "")
                    name, target = tool_names.get(block.get("tool_use_id"), ("?", ""))
                    results.append((len(text), name, target))

    calls = list(usage.values())
    ctx = [u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
           + u.get("cache_creation_input_tokens", 0) for u in calls]
    results.sort(reverse=True)
    return {
        "calls": len(calls),
        "cache_read": sum(u.get("cache_read_input_tokens", 0) for u in calls),
        "cache_write": sum(u.get("cache_creation_input_tokens", 0) for u in calls),
        "output": sum(u.get("output_tokens", 0) for u in calls),
        "avg_ctx": sum(ctx) / len(ctx) if ctx else 0,
        "peak_ctx": max(ctx, default=0),
        "models": models,
        "images": images,
        "compactions": compactions,
        "reads": reads.most_common(top),
        "biggest": results[:top],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("sessions", nargs="*", help="session id prefixes (default: most recent)")
    parser.add_argument("--last", type=int, default=5, help="number of recent sessions (default 5)")
    parser.add_argument("--top", type=int, default=5, help="rows in the re-read / largest lists")
    args = parser.parse_args()

    folder = transcripts_dir()
    files = sorted(folder.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if args.sessions:
        files = [f for f in files if any(f.stem.startswith(s) for s in args.sessions)]
    else:
        files = files[: args.last]
    if not files:
        print(f"No transcripts found in {folder}")
        return 1

    for f in files:
        r = analyse(f, args.top)
        when = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        flag = "  <-- over budget" if r["avg_ctx"] > 150_000 or r["peak_ctx"] > 250_000 else ""
        print(f"\n=== {f.stem[:8]}  {when}  ({f.stat().st_size / 1e6:.0f} MB){flag}")
        print(f"  api calls {r['calls']}   context/call avg {_k(r['avg_ctx'])}  peak {_k(r['peak_ctx'])}"
              f"   compactions {r['compactions']}   images {r['images']}")
        print(f"  cached re-read {_k(r['cache_read'])}   cache write {_k(r['cache_write'])}"
              f"   output {_k(r['output'])}")
        print("  models " + ", ".join(f"{m} x{n}" for m, n in r["models"].most_common() if m))
        if r["reads"]:
            print("  most re-read: " + ", ".join(f"{n} x{c}" for n, c in r["reads"]))
        for size, name, target in r["biggest"]:
            print(f"  {size / 1024:6.0f} KB  {name:<10} {target[:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
