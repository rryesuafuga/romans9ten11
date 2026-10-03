# daily/

One file per run, named `YYYY-MM-DD.md` by the run date in Uganda time (EAT,
UTC+3). The routine runs at 03:07 EAT, so `2026-10-04.md` holds the news that
broke in roughly the 30 hours before 03:07 EAT on 4 October 2026.

Rules the routine follows when writing a file here:

- **One story per bullet**, in the form
  `- **Headline** — one or two neutral sentences. [Source](https://…) · YYYY-MM-DD`
  Keep the headline in bold and every link in `(…)`: `scripts/mark_seen.py`
  reads the file this way to update `seen.json`.
- **Summaries are original.** Short paraphrase, no article text, no quotes
  longer than a phrase. Links and headlines are the reference; the brief is an
  index, not a republication.
- **Same story, several outlets** → one bullet, optionally ending
  `(also: Outlet B, Outlet C)`.
- **Sections appear only when non-empty**, in this order:
  Israel: politics & society · Security & regional · Judea & Samaria ·
  Jewish diaspora · Antisemitism & community safety · Africa & Uganda angle ·
  Also noted.
- **Every file ends with a `## Run report`** whose first line is
  `Run complete: N new items · sources ok X/Y · failed: …` or
  `Run FAILED: reason`. A missing line means the run died part-way.
- **Re-running on the same date rewrites that date's file** rather than
  appending a second copy.

## Template

```markdown
# Daily brief — 2026-10-04 (03:07 EAT)

Window: 2026-10-02 21:07 UTC → 2026-10-04 00:07 UTC (30 h) · 14 new items

## Israel: politics & society
- **Headline** — One or two neutral sentences on what happened and why it matters. [Times of Israel](https://…) · 2026-10-03

## Security & regional
- **Headline** — … [Reuters via Google News](https://…) · 2026-10-03 (also: BBC, Al Jazeera)

## Jewish diaspora
- **Headline** — … [JTA](https://…) · 2026-10-03

## Antisemitism & community safety
- **Headline** — … [Jewish News](https://…) · 2026-10-03

## Africa & Uganda angle
- **Headline** — … [Daily Monitor via Google News](https://…) · 2026-10-03

## Also noted
- **Headline** — one sentence. [Source](https://…) · 2026-10-03

## Run report
Run complete: 14 new items · sources ok 18/20 · failed: Haaretz (HTTP 403), GDELT antisemitism (timeout) · WebSearch calls: 6 · candidates reviewed: 97
```
