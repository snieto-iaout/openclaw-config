#!/usr/bin/env python3
"""Minimal HubSpot CRM API helper (no external deps).

Reads token from env: HUBSPOT_PRIVATE_APP_TOKEN

Supported:
- Search company by domain or name
- Create company
- Create contact
- Create note and associate to company/contact

Docs (approx):
- CRM v3 Objects: companies, contacts, notes
- Search endpoint: /crm/v3/objects/{objectType}/search

This script intentionally keeps mapping simple; property names come from the JSON payload.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from typing import Any, Dict, Optional, List

API_BASE = "https://api.hubapi.com"


class HubSpotHTTPError(RuntimeError):
    def __init__(self, code: int, body: str):
        super().__init__(f"HubSpot HTTP {code}: {body}")
        self.code = code
        self.body = body


def _token() -> str:
    t = os.getenv("HUBSPOT_PRIVATE_APP_TOKEN")
    if not t:
        raise SystemExit("Missing env HUBSPOT_PRIVATE_APP_TOKEN")
    return t


def _request(method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = API_BASE + path
    data = None
    headers = {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise HubSpotHTTPError(e.code, body)


def search_company(domain: Optional[str] = None, name: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    if not domain and not name:
        raise ValueError("domain or name required")

    filters: List[Dict[str, Any]] = []
    if domain:
        filters.append({"propertyName": "domain", "operator": "EQ", "value": domain})
    if name:
        # Use CONTAINS_TOKEN to be tolerant.
        filters.append({"propertyName": "name", "operator": "CONTAINS_TOKEN", "value": name})

    payload = {
        "filterGroups": [{"filters": filters}],
        "limit": limit,
        "properties": ["name", "domain", "hs_object_id"],
    }
    return _request("POST", "/crm/v3/objects/companies/search", payload)


def create_company(properties: Dict[str, Any]) -> Dict[str, Any]:
    return _request("POST", "/crm/v3/objects/companies", {"properties": properties})


def create_contact(properties: Dict[str, Any]) -> Dict[str, Any]:
    return _request("POST", "/crm/v3/objects/contacts", {"properties": properties})


def associate(from_type: str, from_id: str, to_type: str, to_id: str) -> Dict[str, Any]:
    # Default association type
    path = f"/crm/v3/objects/{from_type}/{from_id}/associations/{to_type}/{to_id}/default"
    return _request("PUT", path)


def _create_note_v3(note_body: str) -> Dict[str, Any]:
    # Notes require hs_timestamp in many portals.
    from datetime import datetime, timezone

    ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return _request(
        "POST",
        "/crm/v3/objects/notes",
        {"properties": {"hs_note_body": note_body, "hs_timestamp": ts_ms}},
    )


def _create_note_engagements(note_body: str, company_id: Optional[str], contact_id: Optional[str]) -> Dict[str, Any]:
    # Legacy engagements endpoint; some portals expose this scope as "Engagements" instead of "Notes".
    associations: Dict[str, List[int]] = {}
    if company_id:
        associations["companyIds"] = [int(company_id)]
    if contact_id:
        associations["contactIds"] = [int(contact_id)]

    payload = {
        "engagement": {"type": "NOTE"},
        "associations": associations,
        "metadata": {"body": note_body},
    }
    return _request("POST", "/engagements/v1/engagements", payload)


def create_note(note_body: str, company_id: Optional[str] = None, contact_id: Optional[str] = None) -> Dict[str, Any]:
    # Prefer legacy engagements when we need associations: it works across more portals
    # and avoids association-type headaches for notes.
    if company_id or contact_id:
        try:
            return _create_note_engagements(note_body, company_id, contact_id)
        except HubSpotHTTPError as e:
            if e.code not in (403, 404):
                raise
            # else: fall through to v3 notes

    # v3 notes object (no associations unless portal supports note association types)
    note = _create_note_v3(note_body)
    note_id = str(note.get("id"))
    if company_id:
        try:
            associate("notes", note_id, "companies", str(company_id))
        except HubSpotHTTPError:
            pass
    if contact_id:
        try:
            associate("notes", note_id, "contacts", str(contact_id))
        except HubSpotHTTPError:
            pass
    return note


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cmd_search(args: argparse.Namespace) -> int:
    res = search_company(domain=args.domain, name=args.name, limit=args.limit)
    json.dump(res, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_create_company(args: argparse.Namespace) -> int:
    payload = _read_json(args.json)
    props = payload.get("properties") if "properties" in payload else payload
    res = create_company(props)
    json.dump(res, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_create_contact(args: argparse.Namespace) -> int:
    payload = _read_json(args.json)
    props = payload.get("properties") if "properties" in payload else payload
    res = create_contact(props)
    json.dump(res, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_note(args: argparse.Namespace) -> int:
    res = create_note(args.text, company_id=args.company_id, contact_id=args.contact_id)
    json.dump(res, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_associate(args: argparse.Namespace) -> int:
    res = associate(args.from_type, args.from_id, args.to_type, args.to_id)
    json.dump(res, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("search-company")
    ps.add_argument("--domain")
    ps.add_argument("--name")
    ps.add_argument("--limit", type=int, default=5)
    ps.set_defaults(func=cmd_search)

    pc = sub.add_parser("create-company")
    pc.add_argument("--json", required=True)
    pc.set_defaults(func=cmd_create_company)

    pct = sub.add_parser("create-contact")
    pct.add_argument("--json", required=True)
    pct.set_defaults(func=cmd_create_contact)

    pn = sub.add_parser("create-note")
    pn.add_argument("--company-id")
    pn.add_argument("--contact-id")
    pn.add_argument("--text", required=True)
    pn.set_defaults(func=cmd_note)

    pa = sub.add_parser("associate")
    pa.add_argument("--from-type", required=True)
    pa.add_argument("--from-id", required=True)
    pa.add_argument("--to-type", required=True)
    pa.add_argument("--to-id", required=True)
    pa.set_defaults(func=cmd_associate)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HubSpotHTTPError as e:
        raise SystemExit(str(e))
