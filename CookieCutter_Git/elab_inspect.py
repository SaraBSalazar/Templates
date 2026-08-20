#!/usr/bin/env python3
"""
elab_inspect.py — Look at what your eLabFTW instance actually exposes.

Nothing is created or modified: this only does GET requests.

Usage:
    export ELAB_TOKEN=your_elabftw_api_key      # or it will prompt
    python elab_inspect.py                      # list all experiment templates
    python elab_inspect.py --id 436             # dump one template's extra fields
    python elab_inspect.py --experiment 18325   # dump an existing experiment's fields

Use the last form on an experiment you created by hand from the Agendo_Project
template (the "what it should look like" one) — the field names, types, group ids
and descriptions it prints are exactly what the cookiecutter hook needs to fill in.
"""

import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    sys.exit("❌  pip install requests")

BASE = "https://labbook.gimm.pt/api/v2"


def hdrs(token):
    return {"Authorization": token, "Content-Type": "application/json", "Accept": "application/json"}


def parse_metadata(raw):
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {}


def get(token, path):
    resp = requests.get(f"{BASE}{path}", headers=hdrs(token))
    print(f"    GET {path} → HTTP {resp.status_code}")
    if resp.status_code != 200:
        print(f"    body: {resp.text[:500]}")
        return None
    try:
        return resp.json()
    except ValueError:
        print(f"    (non-JSON response: {resp.text[:200]})")
        return None


def show_fields(meta, label):
    extra = meta.get("extra_fields") or {}
    groups = (meta.get("elabftw") or {}).get("extra_fields_groups") or []

    print(f"\n=== extra fields on {label} ===")
    if groups:
        print("\nField groups:")
        for g in groups:
            print(f"    id {g.get('id')} → {g.get('name')}")
    else:
        print("\n⚠️   No extra_fields_groups — fields would show as 'UNDEFINED GROUP'.")

    if not extra:
        print("\n⚠️   No extra_fields at all on this item.")
        return

    print(f"\n{len(extra)} field(s), in position order:\n")
    ordered = sorted(
        extra.items(),
        key=lambda kv: kv[1].get("position", 0) if isinstance(kv[1], dict) else 0,
    )
    for name, d in ordered:
        if not isinstance(d, dict):
            print(f"  {name}: {d!r}")
            continue
        bits = [f"type={d.get('type', 'text')}"]
        if d.get("group_id") is not None:
            bits.append(f"group_id={d['group_id']}")
        if d.get("position") is not None:
            bits.append(f"position={d['position']}")
        if d.get("required"):
            bits.append("required")
        print(f"  • {name}")
        print(f"      {', '.join(bits)}")
        if d.get("description"):
            print(f"      description: {d['description']}")
        if d.get("options"):
            print(f"      options: {d['options']}")
        if d.get("value") not in (None, ""):
            print(f"      default value: {d['value']!r}")

    print("\n--- raw JSON (paste this if something looks off) ---")
    print(json.dumps(meta, indent=2, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, help="experiment template id to dump")
    ap.add_argument("--experiment", type=int, help="existing experiment id to dump")
    ap.add_argument("--token", default=os.getenv("ELAB_TOKEN"))
    args = ap.parse_args()

    token = args.token
    if not token:
        token = input("eLabFTW API key: ").strip()
    if not token:
        sys.exit("❌  No API key.")

    if args.experiment:
        exp = get(token, f"/experiments/{args.experiment}")
        if exp:
            print(f"\nTitle: {exp.get('title')}")
            show_fields(parse_metadata(exp.get("metadata")), f"experiment {args.experiment}")
        return

    if args.id:
        tmpl = get(token, f"/experiments_templates/{args.id}")
        if tmpl:
            print(f"\nTitle: {tmpl.get('title')}")
            show_fields(parse_metadata(tmpl.get("metadata")), f"template {args.id}")
        return

    # Default: list every template we can see, and say which ones carry extra fields.
    print("\n🔎  Listing experiment templates...")
    templates = get(token, "/experiments_templates")
    if templates is None:
        return
    if not isinstance(templates, list):
        print(json.dumps(templates, indent=2)[:2000])
        return

    print(f"\n{len(templates)} template(s) visible to this API key:\n")
    for t in templates:
        meta = parse_metadata(t.get("metadata"))
        n = len(meta.get("extra_fields") or {})
        marker = f"{n} extra field(s)" if n else "no extra fields in list response"
        print(f"  id {str(t.get('id')):>5}  {t.get('title', '?')!r:45}  {marker}")

    print("\nNext step: pick the id of the Agendo_Project template and run")
    print("    python elab_inspect.py --id <that id>")
    print("Also worth running against a good experiment you made by hand:")
    print("    python elab_inspect.py --experiment <experiment id>")


if __name__ == "__main__":
    main()
