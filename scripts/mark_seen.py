#!/usr/bin/env python3
"""Record the stories published in a daily brief so later runs skip them.

Usage:
    python3 scripts/mark_seen.py daily/2026-10-04.md [--candidates .brief/candidates.json]
        [--seen seen.json] [--keep-days 60]

Every line of the brief that contains a link is treated as one story: the bold
text on the line is the headline, each (http...) link is a URL for it. URLs
already in seen.json are left alone. Entries older than --keep-days are pruned
so the file stays small. Standard library only.
"""
import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brieflib import load_seen, norm_url, title_key  # noqa: E402

LINK_RE = re.compile(r"\((https?://[^)\s]+)\)")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brief", help="path to the daily brief, e.g. daily/2026-10-04.md")
    ap.add_argument("--candidates", default=".brief/candidates.json")
    ap.add_argument("--seen", default="seen.json")
    ap.add_argument("--keep-days", type=int, default=60)
    args = ap.parse_args()

    m = DATE_RE.search(os.path.basename(args.brief))
    brief_date = m.group(1) if m else date.today().isoformat()

    cand_by_url = {}
    if os.path.exists(args.candidates):
        with open(args.candidates, "r", encoding="utf-8") as fh:
            for c in json.load(fh).get("candidates", []):
                cand_by_url[c["url"]] = c

    seen = load_seen(args.seen)
    have = {i.get("url") for i in seen["items"]}
    added = 0
    with open(args.brief, "r", encoding="utf-8") as fh:
        for line in fh:
            urls = [norm_url(u) for u in LINK_RE.findall(line)]
            if not urls:
                continue
            bold = BOLD_RE.search(line)
            headline = bold.group(1).strip() if bold else ""
            for u in urls:
                if not u or u in have:
                    continue
                c = cand_by_url.get(u)
                title = (c or {}).get("title") or headline
                seen["items"].append(
                    {
                        "url": u,
                        "title": title[:200],
                        "title_key": (c or {}).get("title_key") or title_key(title),
                        "source": (c or {}).get("source", ""),
                        "first_seen": brief_date,
                    }
                )
                have.add(u)
                added += 1

    cutoff = (datetime.fromisoformat(brief_date) - timedelta(days=args.keep_days)).date().isoformat()
    before = len(seen["items"])
    seen["items"] = [i for i in seen["items"] if (i.get("first_seen") or brief_date) >= cutoff]
    pruned = before - len(seen["items"])
    seen["items"].sort(key=lambda i: (i.get("first_seen") or "", i.get("url") or ""), reverse=True)
    seen["updated"] = brief_date

    with open(args.seen, "w", encoding="utf-8") as fh:
        json.dump(seen, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"seen.json: +{added} new, {pruned} pruned, {len(seen['items'])} total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
