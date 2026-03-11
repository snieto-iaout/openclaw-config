#!/usr/bin/env python3
"""Session JSONL logging + report for Explorito.

Events are JSON objects, one per line.

Usage:
  session_log.py init --session <id>
  session_log.py append --session <id> --event '<json>'
  session_log.py report --session <id>

Log path:
  automation/explorito/logs/<session>.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, List


def log_path(session: str) -> str:
    return os.path.join("automation", "explorito", "logs", f"{session}.jsonl")


def ensure_dirs() -> None:
    os.makedirs(os.path.join("automation", "explorito", "logs"), exist_ok=True)


def cmd_init(args: argparse.Namespace) -> int:
    ensure_dirs()
    path = log_path(args.session)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            pass
    return 0


def cmd_append(args: argparse.Namespace) -> int:
    ensure_dirs()
    evt = json.loads(args.event)
    evt.setdefault("ts", datetime.now().isoformat(timespec="seconds"))
    with open(log_path(args.session), "a", encoding="utf-8") as f:
        f.write(json.dumps(evt, ensure_ascii=False) + "\n")
    return 0


def _read_events(session: str) -> List[Dict[str, Any]]:
    path = log_path(session)
    events: List[Dict[str, Any]] = []
    if not os.path.exists(path):
        return events
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                continue
    return events


def cmd_report(args: argparse.Namespace) -> int:
    events = _read_events(args.session)

    found = 0
    saved = 0
    discarded = 0
    discard_reasons = Counter()
    by_country = Counter()
    by_segment = Counter()
    saved_scores: List[int] = []
    by_source = Counter()

    # We treat a "decision" event as the final outcome per company.
    for e in events:
        if e.get("event") == "identified":
            found += 1
            src = e.get("source_type")
            if src:
                by_source[src] += 1

        if e.get("event") == "decision":
            decision = e.get("decision")
            if decision == "saved":
                saved += 1
                if e.get("country"):
                    by_country[e["country"]] += 1
                if e.get("segment"):
                    by_segment[e["segment"]] += 1
                if isinstance(e.get("score"), int):
                    saved_scores.append(e["score"])
            elif decision == "discarded":
                discarded += 1
                reason = e.get("reason") or "(sin razón)"
                discard_reasons[reason] += 1

    avg_score = round(sum(saved_scores) / len(saved_scores), 2) if saved_scores else None

    report = {
        "session": args.session,
        "total_found": found,
        "total_saved": saved,
        "total_discarded": discarded,
        "discard_reasons_top": discard_reasons.most_common(5),
        "distribution_by_country": by_country,
        "distribution_by_segment": by_segment,
        "avg_score_saved": avg_score,
        "sources_by_count": by_source,
    }

    print(json.dumps(report, ensure_ascii=False, indent=2, default=list))
    return 0


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init")
    pi.add_argument("--session", required=True)
    pi.set_defaults(func=cmd_init)

    pa = sub.add_parser("append")
    pa.add_argument("--session", required=True)
    pa.add_argument("--event", required=True, help="JSON string")
    pa.set_defaults(func=cmd_append)

    pr = sub.add_parser("report")
    pr.add_argument("--session", required=True)
    pr.set_defaults(func=cmd_report)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
