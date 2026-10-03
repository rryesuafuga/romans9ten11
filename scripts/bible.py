#!/usr/bin/env python3
"""King James Version lookup from the bundled data/kjv.tsv.gz. Standard library only.

Use it to get the exact KJV wording of a passage instead of quoting from memory.

    python3 scripts/bible.py "Psalm 122:6-7" "Romans 10:1"       # print passages
    python3 scripts/bible.py --search "keepeth Israel"             # find verses
    python3 scripts/bible.py --search "peace Jerusalem" --book Psalms --limit 20
    python3 scripts/bible.py --search "saved" --testament NT

Reference forms accepted: "John 3:16", "Psalm 122:6-7", "Isaiah 41:10,13",
"Jeremiah 31:33-34", "Jude 24" (single-chapter books), "1 John 4:9",
"I Samuel 2:2", "Song of Songs 2:4", "Ps 121:4", "Rom 11:26".
"""
import argparse
import gzip
import os
import re
import sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "kjv.tsv.gz")

BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
    "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon",
    "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah",
    "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians",
    "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians",
    "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
    "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation",
]
OT_COUNT = 39
SINGLE_CHAPTER = {"Obadiah", "Philemon", "2 John", "3 John", "Jude"}

_EXTRA_ALIASES = {
    "gen": "Genesis", "ge": "Genesis", "gn": "Genesis",
    "exod": "Exodus", "exo": "Exodus", "ex": "Exodus",
    "lev": "Leviticus", "lv": "Leviticus",
    "num": "Numbers", "nm": "Numbers", "nu": "Numbers",
    "deut": "Deuteronomy", "deu": "Deuteronomy", "dt": "Deuteronomy",
    "josh": "Joshua", "jos": "Joshua",
    "judg": "Judges", "jdg": "Judges", "jg": "Judges",
    "rut": "Ruth", "ru": "Ruth",
    "sam": None,
    "ezr": "Ezra", "neh": "Nehemiah", "ne": "Nehemiah", "esth": "Esther", "est": "Esther",
    "jb": "Job",
    "ps": "Psalms", "psa": "Psalms", "psalm": "Psalms", "pss": "Psalms", "psm": "Psalms",
    "prov": "Proverbs", "pro": "Proverbs", "prv": "Proverbs", "pr": "Proverbs",
    "eccl": "Ecclesiastes", "ecc": "Ecclesiastes", "eccles": "Ecclesiastes", "qoh": "Ecclesiastes",
    "song": "Song of Solomon", "songofsongs": "Song of Solomon", "sos": "Song of Solomon",
    "canticles": "Song of Solomon", "song of songs": "Song of Solomon",
    "isa": "Isaiah", "is": "Isaiah",
    "jer": "Jeremiah", "je": "Jeremiah",
    "lam": "Lamentations", "la": "Lamentations",
    "ezek": "Ezekiel", "eze": "Ezekiel", "ezk": "Ezekiel",
    "dan": "Daniel", "da": "Daniel", "dn": "Daniel",
    "hos": "Hosea", "ho": "Hosea",
    "joe": "Joel", "jl": "Joel",
    "amo": "Amos", "am": "Amos",
    "obad": "Obadiah", "oba": "Obadiah", "ob": "Obadiah",
    "jon": "Jonah", "jnh": "Jonah",
    "mic": "Micah", "mi": "Micah",
    "nah": "Nahum", "na": "Nahum",
    "hab": "Habakkuk", "hb": "Habakkuk",
    "zeph": "Zephaniah", "zep": "Zephaniah", "zp": "Zephaniah",
    "hag": "Haggai", "hg": "Haggai",
    "zech": "Zechariah", "zec": "Zechariah", "zc": "Zechariah",
    "mal": "Malachi", "ml": "Malachi",
    "matt": "Matthew", "mat": "Matthew", "mt": "Matthew",
    "mrk": "Mark", "mar": "Mark", "mk": "Mark", "mr": "Mark",
    "luk": "Luke", "lk": "Luke",
    "joh": "John", "jhn": "John", "jn": "John",
    "act": "Acts", "ac": "Acts",
    "rom": "Romans", "ro": "Romans", "rm": "Romans",
    "gal": "Galatians", "ga": "Galatians",
    "eph": "Ephesians", "ephes": "Ephesians",
    "phil": "Philippians", "php": "Philippians", "pp": "Philippians",
    "col": "Colossians",
    "tit": "Titus", "ti": "Titus",
    "phlm": "Philemon", "philem": "Philemon", "phm": "Philemon",
    "heb": "Hebrews",
    "jas": "James", "jam": "James", "jm": "James",
    "jud": "Jude", "jd": "Jude",
    "rev": "Revelation", "re": "Revelation", "revelations": "Revelation", "apocalypse": "Revelation",
}
_NUMBERED_STEMS = {
    "samuel": "Samuel", "sam": "Samuel", "sa": "Samuel", "sm": "Samuel",
    "kings": "Kings", "kgs": "Kings", "ki": "Kings", "kin": "Kings",
    "chronicles": "Chronicles", "chron": "Chronicles", "chr": "Chronicles", "ch": "Chronicles",
    "corinthians": "Corinthians", "cor": "Corinthians", "co": "Corinthians",
    "thessalonians": "Thessalonians", "thess": "Thessalonians", "thes": "Thessalonians", "th": "Thessalonians",
    "timothy": "Timothy", "tim": "Timothy", "ti": "Timothy", "tm": "Timothy",
    "peter": "Peter", "pet": "Peter", "pe": "Peter", "pt": "Peter",
    "john": "John", "jn": "John", "jhn": "John", "jo": "John", "joh": "John",
}
_ORDINALS = {"1": "1", "i": "1", "first": "1", "1st": "1",
             "2": "2", "ii": "2", "second": "2", "2nd": "2",
             "3": "3", "iii": "3", "third": "3", "3rd": "3"}


class RefError(ValueError):
    pass


def _key(s):
    return re.sub(r"[\s.]+", " ", s.strip().lower()).strip()


def book_index(name):
    """Return 0-based index of a book from a full name or common abbreviation."""
    k = _key(name)
    for i, b in enumerate(BOOKS):
        if k == b.lower():
            return i
    m = re.match(r"^(1st|2nd|3rd|first|second|third|iii|ii|i|1|2|3)\s*([a-z].*)$", k)
    if m and m.group(2).replace(" ", "") in _NUMBERED_STEMS:
        full = f"{_ORDINALS[m.group(1)]} {_NUMBERED_STEMS[m.group(2).replace(' ', '')]}"
        if full in BOOKS:
            return BOOKS.index(full)
    for cand in (k, k.replace(" ", "")):
        if cand in _EXTRA_ALIASES and _EXTRA_ALIASES[cand]:
            return BOOKS.index(_EXTRA_ALIASES[cand])
    raise RefError(f"unknown book name: {name!r}")


_VERSES = None
_CHAPTER_LEN = None


def _load():
    global _VERSES, _CHAPTER_LEN
    if _VERSES is not None:
        return
    _VERSES, _CHAPTER_LEN = {}, {}
    with gzip.open(DATA, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            b, c, v, t = line.rstrip("\n").split("\t", 3)
            b, c, v = int(b) - 1, int(c), int(v)
            _VERSES[(b, c, v)] = t
            if v > _CHAPTER_LEN.get((b, c), 0):
                _CHAPTER_LEN[(b, c)] = v


class Passage:
    def __init__(self, book, verses):
        self.book = book            # 0-based index
        self.verses = verses        # list of (chapter, verse, text)

    @property
    def testament(self):
        return "OT" if self.book < OT_COUNT else "NT"

    @property
    def testament_name(self):
        return "Old Testament" if self.book < OT_COUNT else "New Testament"

    @property
    def text(self):
        return " ".join(t for _, _, t in self.verses)

    @property
    def reference(self):
        name = BOOKS[self.book]
        chapters = sorted({c for c, _, _ in self.verses})
        if name == "Psalms" and len(chapters) == 1:
            name = "Psalm"
        parts = []
        cur_c = None
        run = []

        def flush():
            if not run:
                return
            segs = []
            start = prev = run[0]
            for v in run[1:] + [None]:
                if v is not None and v == prev + 1:
                    prev = v
                    continue
                segs.append(f"{start}" if start == prev else f"{start}-{prev}")
                if v is not None:
                    start = prev = v
            parts.append((cur_c, ",".join(segs)))

        for c, v, _ in self.verses:
            if c != cur_c:
                flush()
                cur_c, run = c, []
            run.append(v)
        flush()
        if BOOKS[self.book] in SINGLE_CHAPTER:
            return f"{name} {';'.join(p for _, p in parts)}"
        if len(parts) == 2 and "," not in parts[0][1] and "," not in parts[1][1]:
            a_c, a = parts[0]
            b_c, b = parts[1]
            a_start = a.split("-")[0]
            b_end = b.split("-")[-1]
            a_end = a.split("-")[-1]
            b_start = b.split("-")[0]
            if a_end == str(_CHAPTER_LEN[(self.book, a_c)]) and b_start == "1":
                return f"{name} {a_c}:{a_start}-{b_c}:{b_end}"
        return f"{name} " + "; ".join(f"{c}:{p}" for c, p in parts)

    def as_dict(self):
        return {
            "reference": self.reference,
            "testament": self.testament,
            "verses": [{"chapter": c, "verse": v, "text": t} for c, v, t in self.verses],
        }


_REF_RE = re.compile(
    r"^\s*(?P<book>(?:[123]|i{1,3}|first|second|third|1st|2nd|3rd)?\s*[A-Za-z][A-Za-z .]*?)\.?\s+"
    r"(?P<loc>\d[\d:,\-–— ;]*)\s*$",
    re.I,
)


def lookup(ref, max_verses=None):
    """Parse a reference and return a Passage. Raises RefError on any problem."""
    _load()
    m = _REF_RE.match(ref or "")
    if not m:
        raise RefError(f"cannot parse reference: {ref!r}")
    b = book_index(m.group("book"))
    loc = re.sub(r"[–—]", "-", m.group("loc")).replace(" ", "")
    if ":" not in loc:
        if BOOKS[b] not in SINGLE_CHAPTER:
            raise RefError(f"{ref!r}: give chapter and verse, e.g. {BOOKS[b]} 3:16")
        loc = "1:" + loc
    verses = []
    for chunk in loc.split(";"):
        if not chunk:
            continue
        cm = re.match(r"^(\d+):(.+)$", chunk)
        if not cm:
            raise RefError(f"{ref!r}: cannot read {chunk!r}")
        chap = int(cm.group(1))
        for piece in cm.group(2).split(","):
            rm = re.match(r"^(\d+)(?:-(?:(\d+):)?(\d+))?$", piece)
            if not rm:
                raise RefError(f"{ref!r}: cannot read verse range {piece!r}")
            v1 = int(rm.group(1))
            c2 = int(rm.group(2)) if rm.group(2) else chap
            v2 = int(rm.group(3)) if rm.group(3) else v1
            if (b, chap) not in _CHAPTER_LEN:
                raise RefError(f"{ref!r}: {BOOKS[b]} has no chapter {chap}")
            if (b, c2) not in _CHAPTER_LEN:
                raise RefError(f"{ref!r}: {BOOKS[b]} has no chapter {c2}")
            c, v = chap, v1
            while True:
                if (b, c, v) not in _VERSES:
                    raise RefError(f"{ref!r}: {BOOKS[b]} {c}:{v} does not exist")
                verses.append((c, v, _VERSES[(b, c, v)]))
                if (c, v) == (c2, v2):
                    break
                if (c, v) > (c2, v2):
                    raise RefError(f"{ref!r}: range runs backwards")
                v += 1
                if v > _CHAPTER_LEN[(b, c)]:
                    c, v = c + 1, 1
            chap = c2
    seen = set()
    uniq = []
    for item in verses:
        if item[:2] not in seen:
            seen.add(item[:2])
            uniq.append(item)
    if max_verses and len(uniq) > max_verses:
        raise RefError(f"{ref!r}: {len(uniq)} verses; keep each passage to {max_verses} verses or fewer")
    return Passage(b, uniq)


def search(words, book=None, testament=None, limit=25):
    _load()
    terms = [w.lower() for w in words.split() if w.strip()]
    bi = book_index(book) if book else None
    out = []
    for (b, c, v), t in _VERSES.items():
        if bi is not None and b != bi:
            continue
        if testament == "OT" and b >= OT_COUNT:
            continue
        if testament == "NT" and b < OT_COUNT:
            continue
        low = t.lower()
        if all(re.search(r"\b" + re.escape(w), low) for w in terms):
            out.append(Passage(b, [(c, v, t)]))
            if len(out) >= limit:
                break
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("refs", nargs="*", help="references to print")
    ap.add_argument("--search", help="words that must all appear in the verse")
    ap.add_argument("--book", help="limit --search to one book")
    ap.add_argument("--testament", choices=["OT", "NT"], help="limit --search to one testament")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()
    if not args.refs and not args.search:
        ap.print_help()
        return 1
    rc = 0
    for r in args.refs:
        try:
            p = lookup(r)
        except RefError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            rc = 1
            continue
        print(f"{p.reference} (KJV, {p.testament_name})")
        for c, v, t in p.verses:
            print(f"  {c}:{v} {t}")
    if args.search:
        hits = search(args.search, args.book, args.testament, args.limit)
        for p in hits:
            c, v, t = p.verses[0]
            print(f"{p.reference} [{p.testament}] {t}")
        if not hits:
            print("no matches")
    return rc


if __name__ == "__main__":
    sys.exit(main())
