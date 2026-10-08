#!/usr/bin/env python3
"""Build the daily prayer guide (Markdown, Word, PDF) from a short JSON spec.

Claude writes the spec (focus lines, scripture references and prayers); this
script checks it against the rules below, inserts the exact King James Version
text from data/kjv.tsv.gz, and writes:

    prayer/YYYY-MM-DD.md   prayer/YYYY-MM-DD.docx   prayer/YYYY-MM-DD.pdf

Usage:
    python3 scripts/build_prayer.py .brief/prayer.json            # check + build
    python3 scripts/build_prayer.py .brief/prayer.json --check    # check only
    python3 scripts/build_prayer.py --example > .brief/prayer.json

Rules (any failure prints every problem and exits 1 without writing files):
  * exactly 5 "news", 5 "protection" and 5 "salvation" points (15 in all)
  * every part has at least 2 Old Testament and 2 New Testament passages
  * every reference exists in the KJV, is at most 4 verses long, and does not
    stop mid-sentence (last verse ending in a comma)
  * no passage is used twice in the guide, nor in the previous 7 days' guides
    (override with --allow-repeats)
  * every prayer addresses the Lord Jesus by name and is 35-200 words
  * news points link to stories in daily/YYYY-MM-DD.md (or, when today's brief
    has fewer than 5 stories, to the previous 6 days' briefs or to none)
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bible import RefError, lookup  # noqa: E402
from brieflib import norm_url  # noqa: E402
import docwriters as dw  # noqa: E402
from docwriters import R  # noqa: E402

REPO_URL = "https://github.com/rryesuafuga/romans9ten11"
GROUPS = [
    ("news", 5, "Praying over today's news"),
    ("protection", 5, "Divine protection of Israel and the Jewish people"),
    ("salvation", 5, "Salvation of the Jewish people in Jesus Christ"),
]
TOTAL_POINTS = sum(n for _, n, _ in GROUPS)
MIN_PER_TESTAMENT = 2   # in each part: at least this many OT and this many NT passages
MAX_VERSES = 4
EPIGRAPH = "Romans 10:1"

EXAMPLE = {
    "date": "2026-10-09",
    "news": [
        {"focus": "Families of the hostages and the negotiators",
         "news": [{"url": "https://example.org/story-1"}],
         "scripture": "Psalm 34:18",
         "prayer": "Lord Jesus, ..."},
        "... 5 news points in all, each linked to stories in today's brief ...",
    ],
    "protection": [
        {"focus": "The Keeper of Israel", "scripture": "Psalm 121:3-4", "prayer": "Lord Jesus, ..."},
        "... 5 protection points in all ...",
    ],
    "salvation": [
        {"focus": "A heart's desire for Israel", "scripture": "Romans 10:1", "prayer": "Lord Jesus, ..."},
        "... 5 salvation points in all ...",
    ],
    "closing": "Lord Jesus, ... Amen.",
}

LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def brief_stories(path):
    """Return {normalised_url: headline} for story bullets in a daily brief."""
    out = {}
    if not os.path.exists(path):
        return out
    in_report = False
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("## "):
                in_report = line.strip().lower().startswith("## run report")
            if in_report or not line.lstrip().startswith("- "):
                continue
            bold = BOLD_RE.search(line)
            for _, url in LINK_RE.findall(line):
                out.setdefault(norm_url(url), bold.group(1).strip() if bold else "")
    return out


def recent_prayer_verses(prayer_dir, date, days=7):
    """{(book, chapter, verse): 'YYYY-MM-DD'} for passages used in earlier guides."""
    used = {}
    start = date - dt.timedelta(days=days)
    for p in glob.glob(os.path.join(prayer_dir, "*.md")):
        m = re.match(r"(\d{4}-\d{2}-\d{2})\.md$", os.path.basename(p))
        if not m:
            continue
        d = dt.date.fromisoformat(m.group(1))
        if not (start <= d < date):
            continue
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                rm = re.match(r"^> — \*\*(.+?)\*\* · KJV · ", line)
                if rm:
                    try:
                        psg = lookup(rm.group(1))
                    except RefError:
                        continue
                    for c, v, _ in psg.verses:
                        used.setdefault((psg.book, c, v), m.group(1))
    return used


def words(s):
    return len(re.findall(r"\b[\w’']+\b", s))


def validate(spec, root, allow_repeats=False):
    errors, warnings = [], []
    try:
        date = dt.date.fromisoformat(str(spec.get("date", "")))
    except ValueError:
        return None, ["'date' must be YYYY-MM-DD"], warnings
    brief_path = os.path.join(root, "daily", f"{date}.md")
    today = brief_stories(brief_path)
    if not os.path.exists(brief_path):
        errors.append(f"{brief_path} does not exist; write the daily brief first")
    recent = {}
    for back in range(1, 7):
        d = date - dt.timedelta(days=back)
        for u, h in brief_stories(os.path.join(root, "daily", f"{d}.md")).items():
            recent.setdefault(u, h)
    used_before = {} if allow_repeats else recent_prayer_verses(os.path.join(root, "prayer"), date)
    seen_here = {}
    resolved = {}
    for key, count, _ in GROUPS:
        items = spec.get(key)
        if not isinstance(items, list) or len(items) != count:
            errors.append(f"'{key}' must be a list of exactly {count} points (got {len(items) if isinstance(items, list) else 'none'})")
            continue
        testaments = []
        resolved[key] = []
        for i, it in enumerate(items, 1):
            where = f"{key}[{i}]"
            if not isinstance(it, dict):
                errors.append(f"{where}: must be an object with focus, scripture and prayer")
                continue
            focus = (it.get("focus") or "").strip()
            if not (3 <= len(focus) <= 90):
                errors.append(f"{where}: 'focus' must be 3-90 characters")
            prayer = (it.get("prayer") or "").strip()
            n = words(prayer)
            if not (35 <= n <= 200):
                errors.append(f"{where}: prayer is {n} words; keep it between 35 and 200")
            if not re.search(r"\bJesus\b", prayer):
                errors.append(f"{where}: the prayer must address the Lord Jesus by name")
            try:
                psg = lookup(it.get("scripture", ""), max_verses=MAX_VERSES)
            except RefError as e:
                errors.append(f"{where}: {e}")
                psg = None
            if psg and psg.verses[-1][2].rstrip().endswith(","):
                errors.append(f"{where}: {psg.reference} stops mid-sentence (ends with a comma); "
                              "extend the range to the end of the sentence or choose another passage")
            if psg:
                testaments.append(psg.testament)
                for c, v, _ in psg.verses:
                    k = (psg.book, c, v)
                    if k in seen_here:
                        errors.append(f"{where}: {psg.reference} overlaps {seen_here[k]} in this guide")
                        break
                    if k in used_before:
                        errors.append(f"{where}: {psg.reference} was used in the {used_before[k]} guide; choose a different passage (or --allow-repeats)")
                        break
                for c, v, _ in psg.verses:
                    seen_here.setdefault((psg.book, c, v), f"{where} ({psg.reference})")
            links = []
            if key == "news":
                raw = it.get("news") or []
                if not isinstance(raw, list) or len(raw) > 3:
                    errors.append(f"{where}: 'news' must be a list of up to 3 links")
                    raw = []
                for ln in raw:
                    u = norm_url((ln or {}).get("url", ""))
                    if u in today:
                        links.append({"url": u, "headline": (ln.get("headline") or today[u] or u).strip(), "today": True})
                    elif u in recent:
                        links.append({"url": u, "headline": (ln.get("headline") or recent[u] or u).strip(), "today": False})
                    else:
                        errors.append(f"{where}: {ln.get('url')!r} is not a story in daily/{date}.md or the previous 6 briefs")
            resolved[key].append({"focus": focus, "prayer": prayer, "passage": psg, "links": links})
        if len(items) == count and len(testaments) == count:
            n_ot, n_nt = testaments.count("OT"), testaments.count("NT")
            if n_ot < MIN_PER_TESTAMENT or n_nt < MIN_PER_TESTAMENT:
                errors.append(f"'{key}' needs at least {MIN_PER_TESTAMENT} Old Testament and {MIN_PER_TESTAMENT} "
                              f"New Testament passages (has {n_ot} OT, {n_nt} NT)")
    if "news" in resolved and len(resolved["news"]) == 5:
        linked_today = sum(1 for p in resolved["news"] if any(l["today"] for l in p["links"]))
        need = min(5, len(today))
        if linked_today < need:
            errors.append(f"only {linked_today} news points link to today's brief, which has {len(today)} stories; "
                          f"at least {need} must")
        for i, p in enumerate(resolved["news"], 1):
            if not p["links"] and len(today) >= 5:
                errors.append(f"news[{i}]: link it to a story in today's brief")
    closing = (spec.get("closing") or "").strip()
    if closing and not re.search(r"\bJesus\b", closing):
        errors.append("'closing' must address the Lord Jesus by name")
    if closing and words(closing) > 150:
        errors.append("'closing' must be 150 words or fewer")
    return {"date": date, "groups": resolved, "closing": closing, "today_count": len(today)}, errors, warnings


def long_date(d):
    return f"{d.strftime('%A')}, {d.day} {d.strftime('%B')} {d.year}"


def build_blocks(v, for_markdown):
    d = v["date"]
    brief_url = f"../daily/{d}.md" if for_markdown else f"{REPO_URL}/blob/main/daily/{d}.md"
    epi = lookup(EPIGRAPH)
    blocks = [
        {"t": "title", "text": f"Daily Prayer Guide — {long_date(d)}"},
        {"t": "subtitle", "text": "Praying to the Lord Jesus for Israel, Jews in Israel, Jews in the diaspora, and Judea and Samaria"},
        {"t": "meta", "runs": [R("Based on the "), R(f"daily news brief for {d.day} {d.strftime('%B')} {d.year}", url=brief_url),
                               R(f" · Scripture: King James Version (public domain) · {TOTAL_POINTS} prayer points")]},
        {"t": "epigraph", "text": epi.text, "ref": epi.reference},
        {"t": "h1", "text": "At a glance"},
    ]
    glance, n = [], 0
    for key, _, _ in GROUPS:
        for p in v["groups"][key]:
            n += 1
            glance.append((n, [R(p["focus"], b=True), R(f" — {p['passage'].reference}")]))
    blocks.append({"t": "glance", "items": glance})
    n = 0
    for part, (key, count, heading) in enumerate(GROUPS, 1):
        first, last = n + 1, n + count
        blocks.append({"t": "h1", "text": f"Part {part} · {heading} (points {first}–{last})"})
        for p in v["groups"][key]:
            n += 1
            blocks.append({"t": "h2", "text": f"{n}. {p['focus']}"})
            if key == "news":
                runs = [R("In the news: ", b=True)]
                if p["links"]:
                    for j, ln in enumerate(p["links"]):
                        if j:
                            runs.append(R("; "))
                        runs.append(R(ln["headline"], url=ln["url"]))
                        if not ln["today"]:
                            runs.append(R(" (earlier this week)"))
                else:
                    runs.append(R("an ongoing story from this week's briefs"))
                blocks.append({"t": "para", "style": "NewsLine", "runs": runs})
            psg = p["passage"]
            blocks.append({"t": "scripture", "verses": psg.verses, "ref": psg.reference, "testament": psg.testament_name})
            blocks.append({"t": "prayer", "paras": [s.strip() for s in re.split(r"\n\s*\n", p["prayer"]) if s.strip()]})
    if v["closing"]:
        blocks.append({"t": "h1", "text": "Closing prayer"})
        blocks.append({"t": "para", "style": "Closing", "runs": [R(v["closing"], i=True)]})
    blocks.append({"t": "rule"})
    blocks.append({"t": "meta", "runs": [R(
        "Scripture quotations are from the King James Version (1769 text), which is in the public domain. "
        "News items are summarised in the daily brief; follow the links for the original reporting. "
        f"Generated by the romans9ten11 daily routine for {d}.")]})
    return blocks


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", nargs="?", help="path to the JSON spec")
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    ap.add_argument("--out-dir", default=None, help="default: <root>/prayer")
    ap.add_argument("--check", action="store_true", help="validate only")
    ap.add_argument("--allow-repeats", action="store_true")
    ap.add_argument("--pdf-engine", choices=["builtin", "libreoffice"], default="builtin",
                    help="builtin (default, standard library) or libreoffice (needs LibreOffice Writer; falls back to builtin)")
    ap.add_argument("--example", action="store_true", help="print an example spec and exit")
    args = ap.parse_args()
    if args.example:
        print(json.dumps(EXAMPLE, indent=2, ensure_ascii=False))
        return 0
    if not args.spec:
        ap.error("spec path required")
    root = os.path.abspath(args.root)
    with open(args.spec, encoding="utf-8") as fh:
        spec = json.load(fh)
    v, errors, warnings = validate(spec, root, allow_repeats=args.allow_repeats)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} problem(s) in {args.spec}:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    summary = {k: [p["passage"].testament for p in v["groups"][k]] for k, _, _ in GROUPS}
    print("spec OK: " + "; ".join(f"{k} {''.join('O' if t == 'OT' else 'N' for t in ts)}" for k, ts in summary.items())
          + f" · today's brief has {v['today_count']} stories")
    if args.check:
        return 0
    out_dir = args.out_dir or os.path.join(root, "prayer")
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, str(v["date"]))
    title = f"Daily Prayer Guide — {long_date(v['date'])}"
    footer = f"Daily Prayer Guide · {v['date'].day} {v['date'].strftime('%B')} {v['date'].year}"
    with open(base + ".md", "w", encoding="utf-8") as fh:
        fh.write(dw.to_markdown(build_blocks(v, for_markdown=True)))
    file_blocks = build_blocks(v, for_markdown=False)
    dw.write_docx(file_blocks, base + ".docx", title, footer)
    engine = "builtin"
    if args.pdf_engine == "libreoffice" and dw.docx_to_pdf(base + ".docx", base + ".pdf"):
        engine = "libreoffice"
    else:
        dw.write_pdf(file_blocks, base + ".pdf", title, footer)
    for ext in (".md", ".docx", ".pdf"):
        print(f"wrote {os.path.relpath(base + ext, root)} ({os.path.getsize(base + ext)} bytes)")
    print(f"pdf engine: {engine}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
