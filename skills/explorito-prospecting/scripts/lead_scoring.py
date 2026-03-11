#!/usr/bin/env python3
"""Lead scoring + disqualification rules for Munily ICP.

Usage:
  lead_scoring.py score --in company.json

Input is a JSON object matching (roughly) references/company-schema.json.
Outputs JSON with: qualified(bool), score(int), breakdown, disqualify_reason.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple


SEGMENT_POINTS = {
    "Administración PH": 25,
    "Seguridad Privada": 25,
    "Constructora": 20,
}

COUNTRY_POINTS = {
    "Colombia": 10,
    "Panamá": 10,
    "Estados Unidos": 5,
}

SOURCE_POINTS = {
    "Directorio": 10,
    "LinkedIn": 5,  # only if profile complete+active; model via flags
    "Website": 5,
}


@dataclass
class ScoreResult:
    qualified: bool
    score: int
    breakdown: Dict[str, int]
    disqualify_reason: Optional[str] = None


def _get_int(v: Any) -> Optional[int]:
    try:
        if v is None:
            return None
        if isinstance(v, bool):
            return None
        return int(v)
    except Exception:
        return None


def disqualify(company: Dict[str, Any]) -> Optional[str]:
    seg = company.get("segment")
    if seg not in ("Administración PH", "Seguridad Privada", "Constructora"):
        return "No pertenece a segmentos ICP"

    country = company.get("country")
    if country not in ("Colombia", "Panamá", "Estados Unidos"):
        return "No opera en CO/PA/US"

    employees = _get_int(company.get("employees_est"))
    if employees is not None and employees < 5:
        return "Menos de 5 empleados"

    last_year = _get_int(company.get("activity_last_year"))
    if last_year is not None:
        # Consider inactive if last activity older than 2 full years.
        from datetime import datetime

        now_year = datetime.now().year
        if now_year - last_year > 2:
            return "Inactiva por más de 2 años"

    dp = company.get("digital_presence") or {}
    has_any = bool(
        dp.get("has_website")
        or dp.get("has_linkedin")
        or dp.get("has_directory_listing")
        or dp.get("has_recent_news")
    )
    if not has_any:
        return "Sin presencia digital verificable"

    return None


def score_company(company: Dict[str, Any]) -> ScoreResult:
    reason = disqualify(company)
    if reason:
        return ScoreResult(qualified=False, score=0, breakdown={}, disqualify_reason=reason)

    breakdown: Dict[str, int] = {}

    seg = company.get("segment")
    breakdown["segment"] = SEGMENT_POINTS.get(seg, 0)

    country = company.get("country")
    breakdown["country"] = COUNTRY_POINTS.get(country, 0)

    # Size scoring depends on segment
    if seg == "Administración PH":
        props = _get_int(company.get("properties_managed_est"))
        if props is not None:
            if props > 50:
                breakdown["size"] = 20
            elif 10 <= props <= 49:
                breakdown["size"] = 15
            else:
                breakdown["size"] = 5
        else:
            breakdown["size"] = 0

    elif seg == "Seguridad Privada":
        employees = _get_int(company.get("employees_est"))
        if employees is not None:
            if employees > 100:
                breakdown["size"] = 10
            elif 20 <= employees <= 99:
                breakdown["size"] = 5
            else:
                breakdown["size"] = 0
        else:
            breakdown["size"] = 0

    elif seg == "Constructora":
        ppy = company.get("projects_per_year_est")
        try:
            ppy_f = float(ppy) if ppy is not None else None
        except Exception:
            ppy_f = None
        if ppy_f is not None:
            if ppy_f > 3:
                breakdown["size"] = 10
            elif 1 <= ppy_f <= 3:
                breakdown["size"] = 5
            else:
                breakdown["size"] = 0
        else:
            breakdown["size"] = 0

    # Source points (accumulable)
    dp = company.get("digital_presence") or {}
    source_type = (company.get("source") or {}).get("type")
    source_points = 0

    if source_type == "Directorio":
        source_points += SOURCE_POINTS["Directorio"]

    # LinkedIn: count only if has_linkedin and we consider it active/complete.
    if dp.get("has_linkedin"):
        # Optional flags (if present) to be stricter
        li_ok = company.get("linkedin_profile_complete_active")
        if li_ok is None or bool(li_ok):
            source_points += SOURCE_POINTS["LinkedIn"]

    if dp.get("has_website"):
        source_points += SOURCE_POINTS["Website"]

    breakdown["source"] = int(source_points)

    total = sum(breakdown.values())
    qualified = total >= 40

    return ScoreResult(qualified=qualified, score=int(total), breakdown=breakdown)


def cmd_score(args: argparse.Namespace) -> int:
    with open(args.input, "r", encoding="utf-8") as f:
        company = json.load(f)

    res = score_company(company)
    json.dump(asdict(res), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")

    return 0


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("score", help="Score one company JSON")
    ps.add_argument("--in", dest="input", required=True, help="Path to company.json")
    ps.set_defaults(func=cmd_score)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
