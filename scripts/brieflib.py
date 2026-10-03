"""Shared helpers for the daily-brief scripts. Standard library only."""
import hashlib
import re
import urllib.parse

TRACKING_PARAMS = {
    "fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "ncid", "ocid",
    "cmpid", "smid", "smtyp", "partner", "ito",
}


def norm_url(url: str) -> str:
    """Canonical form of a URL for de-duplication (no tracking params, no fragment)."""
    url = (url or "").strip()
    if not url:
        return ""
    parts = urllib.parse.urlsplit(url)
    scheme = (parts.scheme or "https").lower()
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    query = [
        (k, v)
        for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS
    ]
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return urllib.parse.urlunsplit(
        (scheme, host, path, urllib.parse.urlencode(query, doseq=True), "")
    )


_WORD_RE = re.compile(r"[^a-z0-9֐-׿؀-ۿ ]+")


def title_key(title: str, words: int = 12) -> str:
    """Stable fingerprint of a headline, so the same story from two outlets collides."""
    t = (title or "").lower()
    t = _WORD_RE.sub(" ", t)
    toks = [w for w in t.split() if w]
    if not toks:
        return ""
    return hashlib.sha1(" ".join(toks[:words]).encode("utf-8")).hexdigest()[:16]


def load_seen(path: str) -> dict:
    import json
    import os

    if not os.path.exists(path):
        return {"version": 1, "updated": None, "items": []}
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    data.setdefault("version", 1)
    data.setdefault("updated", None)
    data.setdefault("items", [])
    return data
