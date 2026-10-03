# Routine prompt — daily news brief and prayer guide

The scheduled routine sends a short prompt that tells the run to open this file
and follow **Full instructions**. Edit this file to change what the routine
does; the change applies from the next run, with no need to touch the routine.

The purpose of the repository, from `README.md`: *Pray to Lord Jesus for
Israel, Jews in Israel, Jews in diaspora and Judea and Samaria.* The news brief
exists to inform that prayer; the prayer guide is the main deliverable.

## Full instructions

You are running unattended as a scheduled Claude Code routine for the GitHub
repository `rryesuafuga/romans9ten11`. Nobody will answer questions, so make
reasonable decisions yourself and record them in the run report.

The repository owner has explicitly authorised, and requires, that you commit
directly on `main` and push to `main`. Do not create a `claude/` branch and do
not open a pull request.

### Fixed facts

- Schedule: 03:07 Uganda time (EAT, UTC+3, no daylight saving) = 00:07 UTC.
- The run date is the Uganda date: `DATE=$(date -u -d '+3 hours' +%F)`.
- Files you may create or change:
  - `daily/$DATE.md` (news brief), `seen.json`
  - `prayer/$DATE.md`, `prayer/$DATE.docx`, `prayer/$DATE.pdf` (prayer guide)
  - the blocks between `<!-- LATEST_START -->`/`<!-- LATEST_END -->` and
    `<!-- ROLLING_SUMMARY_START -->`/`<!-- ROLLING_SUMMARY_END -->` in `README.md`
- Never delete or rewrite earlier days' files. Do not edit `scripts/`,
  `routine/`, `data/`, `prayer/scripture-bank.md` or `.github/`. Do not install
  packages.
- Format rules: `daily/README.md` (brief) and `prayer/README.md` (guide). Read
  both before writing.

### Phase A — news brief

1. `git checkout main && git pull --ff-only origin main`
2. Read `daily/README.md`, `prayer/README.md`, `README.md`, and the two most
   recent files in `daily/`.
3. `python3 scripts/fetch_candidates.py --hours 30 --out .brief/candidates.json`
   then read `.brief/candidates.json`. It already excludes stories recorded in
   `seen.json`. Note failed sources (`sources[].error`). Exit code 2 means
   every source failed (usually the environment's network policy): continue
   with WebSearch only and say so in the run report.
4. Fill gaps with WebSearch: 4 to 8 searches, roughly one per theme (Israel
   politics and society; security and the region; Judea and Samaria; Jewish
   diaspora communities; antisemitism incidents; Israel with Africa or
   Uganda). Keep only stories from the last ~30 hours not already covered.
   When the fetch script reached no sources, run these searches with
   `mode: "extended"`, because standard search often returns week-old pages;
   otherwise `"standard"` is enough. Put the current date in each query.
   If nothing dated within the window can be confirmed for a theme, leave the
   theme out rather than filling it with older stories.
5. Triage: significant, new, verifiable from a named outlet. Aim for 10 to 25
   bullets; fewer on a quiet day. Merge the same story from several outlets.
   Do not invent or embellish. A candidate you cannot confirm goes under
   "Also noted" with one sentence describing the headline only, or is dropped.
6. Write `daily/$DATE.md` exactly as `daily/README.md` specifies.
   **If `daily/$DATE.md` already exists** (a second run on the same Uganda
   date), keep every existing bullet, add the new stories to the right
   sections, update the Window line, and append a second line to the run
   report. Never drop existing bullets.
7. `python3 scripts/mark_seen.py daily/$DATE.md --candidates .brief/candidates.json`
8. Replace the rolling-summary block in `README.md` with 5 to 10 neutral
   bullets on the last 7 days (read the last 7 daily files), ending with
   `_Updated $DATE from daily briefs YYYY-MM-DD to YYYY-MM-DD._`
9. Commit and push the brief now, so it is saved even if Phase B fails:
   ```
   git add daily/$DATE.md seen.json README.md
   git commit -m "Daily brief $DATE: N new items"
   git push origin main
   ```

### Phase B — prayer guide (10 points)

The guide prays to the Lord Jesus for Israel, Jews in Israel, Jews in the
diaspora, and Judea and Samaria. It has exactly 10 points, each one a
King James Version passage plus a prayer the reader can pray:

| Part | Points | Focus | Scripture rule |
|---|---|---|---|
| 1 | 5 | The issues in today's news brief | Old and New Testament both present; aim for at least 2 of each |
| 2 | 3 | Divine protection of the nation of Israel and of Jews everywhere | Old and New Testament both present |
| 3 | 2 | Salvation of Jewish people: coming to faith in Jesus as Messiah and Lord | One Old Testament, one New Testament |

10. Read `daily/$DATE.md`, the "At a glance" lists of the last 7 files in
    `prayer/`, and `prayer/scripture-bank.md`.
11. Part 1: pick 5 distinct, prayer-worthy stories from today's brief: people
    in danger, hostages, the bereaved and wounded, leaders facing decisions,
    attacks on Jewish communities, diaspora life, Judea and Samaria, and any
    Uganda or Africa angle. Each point links to 1 to 3 stories by their exact
    URLs in `daily/$DATE.md`. If today's brief has fewer than 5 stories, use
    stories from the previous 6 briefs or an ongoing theme for the rest.
12. Choose passages. Use `prayer/scripture-bank.md` for ideas and any other
    fitting passage. Confirm the wording and range of every choice with
    `python3 scripts/bible.py "<reference>"`, or find one with
    `python3 scripts/bible.py --search "<words>"`. Never quote Scripture from
    memory: you supply only the reference and the build script inserts the
    exact KJV text. 1 to 4 verses, ending at a sentence break. No passage
    from the previous 7 days' guides.
13. Write each prayer as `prayer/README.md` describes: first person,
    addressed to the Lord Jesus by name, 60 to 140 words, drawn from the
    passage and specific to the news. Also write a closing prayer of 40 to 90
    words.
14. Save the spec as `.brief/prayer.json` in the format of
    `python3 scripts/build_prayer.py --example`, then run
    `python3 scripts/build_prayer.py .brief/prayer.json`.
    It checks every rule and lists all problems. Fix them and run it again
    until it prints `spec OK` and writes the three files. If it is a re-run
    for the same date, the guide is simply rebuilt from today's merged brief.
15. Replace the block between `<!-- LATEST_START -->` and `<!-- LATEST_END -->`
    in `README.md` with:
    ```
    **Latest ($DATE):** prayer guide [Markdown](prayer/$DATE.md) · [Word](prayer/$DATE.docx) · [PDF](prayer/$DATE.pdf) · [news brief](daily/$DATE.md)
    ```
16. Commit and push:
    ```
    git add prayer/$DATE.md prayer/$DATE.docx prayer/$DATE.pdf README.md
    git commit -m "Prayer guide $DATE: 10 points"
    git push origin main
    ```
    If a push is rejected as non-fast-forward, run `git pull --rebase origin main`
    and push again. Confirm with `git log origin/main -2 --oneline`.

### Final message

End with exactly one line:

- `Run complete: N new items · prayer guide 10 points (md, docx, pdf) · sources ok X/Y · pushed <short sha>`
- or `Run FAILED: <phase and one-line reason>`. Commit and push whatever was
  produced before failing, and describe the problem in the brief's run report.

If a PushNotification tool is available, send that same line as one
notification before you finish, so the owner sees the result on their phone.

### Standards for the news brief

- Neutral and factual. Attribute claims to the outlet or official who made
  them. No loaded adjectives, no speculation.
- Original summaries only; headlines may be reproduced; no quotes beyond a few
  words. Every bullet links a named outlet.
- If the day's coverage is one-sided, say in the run report that the brief
  reflects what the sources carried.
- Non-English items: English headline in bold, language code in brackets,
  for example `(fr)`.
- Keep going when a source fails and report it. If a source has failed three
  days running, say so in the run report so a person can remove it.
