#!/usr/bin/env python3
"""Fetch candidate news items for the daily brief.

Reads routine/sources.json and seen.json, pulls every source (Google News RSS
queries, GDELT DOC API queries, curated RSS/Atom feeds), normalises and
de-duplicates the items, drops anything already covered, and writes a JSON
file for Claude to triage. Standard library only.

Usage:
    python3 scripts/fetch_candidates.py [--hours 30] [--out .brief/candidates.json]
        [--sources routine/sources.json] [--seen seen.json] [--max 150] [--timeout 25]

A failing source never aborts the run: it is recorded under "sources" in the
output with its error so the brief can report it. Exit code 2 only if every
source failed.
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brieflib import load_seen, norm_url, title_key  # noqa: E402

UA = "Mozilla/5.0 (compatible; romans9ten11-daily-brief/1.0; +https://github.com/rryesuafuga/romans9ten11)"
GDELT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"
ATOM = "{http://www.w3.org/2005/Atom}"
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def clean_text(s: str, limit: int = 280) -> str:
    s = html.unescape(TAG_RE.sub(" ", s or ""))
    s = WS_RE.sub(" ", s).strip()
    return s[: limit - 1] + "…" if len(s) > limit else s


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        return parsedate_to_datetime(s).astimezone(timezone.utc)
    except Exception:
        pass
    try:
        return datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def fetch(url: str, timeout: int) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _text(el, *names):
    for n in names:
        child = el.find(n)
        if child is not None and (child.text or "").strip():
            return child.text.strip()
    return ""


def parse_feed(data: bytes, source_name: str):
    """Parse RSS 2.0 or Atom. Returns list of raw item dicts."""
    root = ET.fromstring(data)
    items = []
    if root.tag == f"{ATOM}feed":
        for e in root.findall(f"{ATOM}entry"):
            link = ""
            for l in e.findall(f"{ATOM}link"):
                if l.get("rel", "alternate") == "alternate" and l.get("href"):
                    link = l.get("href")
                    break
            items.append(
                {
                    "title": _text(e, f"{ATOM}title"),
                    "url": link,
                    "published": _text(e, f"{ATOM}published", f"{ATOM}updated"),
                    "summary": _text(e, f"{ATOM}summary", f"{ATOM}content"),
                    "source": source_name,
                }
            )
        return items
    channel = root.find("channel")
    if channel is None:
        raise ValueError("not RSS or Atom")
    for it in channel.findall("item"):
        src_el = it.find("source")
        outlet = (src_el.text or "").strip() if src_el is not None else ""
        title = _text(it, "title")
        if outlet and title.endswith(" - " + outlet):
            title = title[: -(len(outlet) + 3)].strip()
        items.append(
            {
                "title": title,
                "url": _text(it, "link") or (it.find("guid").text if it.find("guid") is not None else ""),
                "published": _text(it, "pubDate", "{http://purl.org/dc/elements/1.1/}date"),
                "summary": _text(it, "description", "{http://purl.org/rss/1.0/modules/content/}encoded"),
                "source": outlet or source_name,
            }
        )
    return items


def parse_gdelt(data: bytes, source_name: str):
    text = data.decode("utf-8", errors="replace").strip()
    if not text.startswith("{"):
        raise ValueError("GDELT returned non-JSON: " + clean_text(text, 160))
    payload = json.loads(text)
    items = []
    for a in payload.get("articles", []):
        items.append(
            {
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "published": a.get("seendate", ""),
                "summary": "",
                "source": a.get("domain", "") or source_name,
                "language": a.get("language", ""),
                "country": a.get("sourcecountry", ""),
            }
        )
    return items


def gdelt_url(src: dict, hours: int) -> str:
    params = {
        "query": src["query"],
        "mode": "artlist",
        "maxrecords": str(src.get("maxrecords", 75)),
        "timespan": f"{hours}h",
        "format": "json",
        "sort": "datedesc",
    }
    return GDELT_ENDPOINT + "?" + urllib.parse.urlencode(params)


def relevant(item: dict, terms) -> bool:
    hay = (item.get("title", "") + " " + item.get("summary", "")).lower()
    return any(t in hay for t in terms)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hours", type=int, default=30, help="look-back window in hours (default 30)")
    ap.add_argument("--out", default=".brief/candidates.json")
    ap.add_argument("--sources", default="routine/sources.json")
    ap.add_argument("--seen", default="seen.json")
    ap.add_argument("--max", type=int, default=150, help="cap on candidates written")
    ap.add_argument("--timeout", type=int, default=25)
    args = ap.parse_args()

    with open(args.sources, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    terms = [t.lower() for t in cfg.get("relevance_terms", [])]
    seen = load_seen(args.seen)
    seen_urls = {i.get("url") for i in seen["items"] if i.get("url")}
    seen_keys = {i.get("title_key") for i in seen["items"] if i.get("title_key")}

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=args.hours)

    report = []
    by_url = {}
    by_key = {}
    dropped_seen = 0
    dropped_old = 0
    dropped_irrelevant = 0
    gdelt_calls = 0

    for src in cfg.get("sources", []):
        name = src.get("name", "unnamed")
        kind = src.get("type", "rss")
        entry = {"name": name, "type": kind, "ok": False, "fetched": 0, "kept": 0, "error": None}
        try:
            if kind == "gdelt":
                if gdelt_calls:
                    time.sleep(5)  # GDELT asks for at most one request every 5 seconds
                gdelt_calls += 1
                url = gdelt_url(src, args.hours)
                raw = parse_gdelt(fetch(url, args.timeout), name)
            else:
                url = src["url"]
                raw = parse_feed(fetch(url, args.timeout), name)
            entry["ok"] = True
            entry["fetched"] = len(raw)
        except urllib.error.HTTPError as e:
            entry["error"] = f"HTTP {e.code}"
            report.append(entry)
            log(f"[fail] {name}: HTTP {e.code}")
            continue
        except urllib.error.URLError as e:
            entry["error"] = f"URLError: {clean_text(str(getattr(e, 'reason', e)), 120) or 'unreachable'}"
            report.append(entry)
            log(f"[fail] {name}: {entry['error']}")
            continue
        except Exception as e:  # parse errors, timeouts, bad payloads
            entry["error"] = f"{type(e).__name__}: {clean_text(str(e), 120) or 'no detail'}"
            report.append(entry)
            log(f"[fail] {name}: {entry['error']}")
            continue

        kept = 0
        for it in raw:
            u = norm_url(it.get("url", ""))
            if not u or not it.get("title"):
                continue
            dt = parse_date(it.get("published"))
            if dt is not None and dt < cutoff:
                dropped_old += 1
                continue
            if src.get("filter", False) and terms and not relevant(it, terms):
                dropped_irrelevant += 1
                continue
            k = title_key(it["title"])
            if u in seen_urls or (k and k in seen_keys):
                dropped_seen += 1
                continue
            cand = {
                "title": clean_text(it["title"], 200),
                "url": u,
                "source": it.get("source") or name,
                "feed": name,
                "published": dt.isoformat(timespec="minutes") if dt else None,
                "summary": clean_text(it.get("summary", "")),
                "title_key": k,
            }
            if it.get("language"):
                cand["language"] = it["language"]
            if it.get("country"):
                cand["country"] = it["country"]
            if u in by_url:
                by_url[u].setdefault("also_in", []).append(name)
                continue
            if k and k in by_key:
                other = by_key[k]
                other.setdefault("also_in", []).append(f"{cand['source']} <{u}>")
                continue
            by_url[u] = cand
            if k:
                by_key[k] = cand
            kept += 1
        entry["kept"] = kept
        report.append(entry)
        log(f"[ok]   {name}: {len(raw)} fetched, {kept} new")

    cands = list(by_url.values())
    cands.sort(key=lambda c: c.get("published") or "", reverse=True)
    truncated = max(0, len(cands) - args.max)
    cands = cands[: args.max]

    out = {
        "generated_at": now.isoformat(timespec="seconds"),
        "window_hours": args.hours,
        "window_start": cutoff.isoformat(timespec="minutes"),
        "sources_ok": sum(1 for r in report if r["ok"]),
        "sources_total": len(report),
        "dropped": {"already_seen": dropped_seen, "outside_window": dropped_old, "irrelevant": dropped_irrelevant, "over_cap": truncated},
        "sources": report,
        "candidates": cands,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    log(
        f"candidates: {len(cands)} new from {out['sources_ok']}/{out['sources_total']} sources "
        f"(seen {dropped_seen}, old {dropped_old}, irrelevant {dropped_irrelevant}, over cap {truncated}) -> {args.out}"
    )
    if report and out["sources_ok"] == 0:
        log("ERROR: every source failed. Check the environment's network access (Custom, with the feed domains allowed).")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
