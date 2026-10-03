# Routine prompt — Israel & Jewish diaspora daily brief

Two ways to use this file:

- **Recommended:** paste only the *short prompt* below into the routine's prompt
  box. The run then reads this file from the repository, so editing it here
  changes the next run without touching the routine.
- **Fallback:** paste the whole *full instructions* section into the prompt box
  instead. Keep the two in sync if you do.

## Short prompt (paste this into the routine)

```
You are running unattended as a scheduled Claude Code routine in the repository
rryesuafuga/romans9ten11. Open routine/PROMPT.md and follow the section "Full
instructions" exactly. Hard rules even if that file is missing: work on and
push to main directly, never a claude/ branch and never a pull request; write
daily/$(date -u +%F).md and update seen.json and the rolling summary in
README.md only; end your final message with one line starting
"Run complete:" or "Run FAILED:".
```

## Full instructions

You are running unattended as a scheduled Claude Code routine in the GitHub
repository `rryesuafuga/romans9ten11`. Your job today is to produce the daily
news brief on Israel, Jews in Israel, Judea and Samaria, and Jewish diaspora
communities worldwide, and commit it to `main`. Nobody will answer questions,
so make reasonable decisions yourself and record them in the run report.

### Fixed facts

- Run time: 03:07 Uganda time (EAT, UTC+3), which is 00:07 UTC. The brief date
  is today's UTC date: `DATE=$(date -u +%F)`.
- Files you own: `daily/$DATE.md`, `seen.json`, and the block between
  `<!-- ROLLING_SUMMARY_START -->` and `<!-- ROLLING_SUMMARY_END -->` in
  `README.md`. Do not change anything else. Never delete or rewrite earlier
  daily files.
- Format rules and the template are in `daily/README.md`. Read it first.
- Work on and push to `main` directly. Do not create a `claude/` branch and do
  not open a pull request.

### Steps

1. `git checkout main && git pull --ff-only origin main`
2. Read `daily/README.md`, `README.md`, and the two most recent files in
   `daily/` so you know the format and what was covered already.
3. Collect candidates:
   `python3 scripts/fetch_candidates.py --hours 30 --out .brief/candidates.json`
   Then read `.brief/candidates.json`. It already excludes stories recorded in
   `seen.json`. Note which sources failed (`sources[].error`); you will report
   them. If the script exits with code 2 (every source failed), continue with
   WebSearch only and say so in the run report.
4. Fill gaps with WebSearch: at most 4 to 8 searches, one per theme (Israel
   politics and society; security and the region; Judea and Samaria; Jewish
   diaspora communities; antisemitism incidents; Israel and Africa or Uganda).
   Keep only stories from the last ~30 hours that are not already in the
   candidates or in the recent daily files.
5. Triage. Pick the stories that matter: significant, new, and verifiable from
   a named outlet. Aim for 10 to 25 bullets; fewer on a quiet day is fine.
   Merge the same story from several outlets into one bullet. Prefer primary
   reporting over commentary. Do not invent or embellish. If a candidate's
   title is all you have and WebSearch cannot confirm it, leave it out, or put
   it under "Also noted" with one sentence describing the headline only.
6. Write `daily/$DATE.md` using the template exactly: bold headline, one or two
   neutral sentences in your own words, `[Source](url)`, the published date,
   sections in the fixed order, only non-empty sections, and a `## Run report`
   at the end. If `daily/$DATE.md` already exists (a re-run), rewrite it rather
   than appending. If there are no new items, still write the file with the
   line `Run complete: 0 new items …` in the run report.
7. `python3 scripts/mark_seen.py daily/$DATE.md --candidates .brief/candidates.json`
8. Update the rolling summary in `README.md`: replace only the text between
   the two markers with 5 to 10 bullets describing the state of the story over
   the last 7 days (read the last 7 daily files), then a final line
   `_Updated $DATE from daily briefs YYYY-MM-DD to YYYY-MM-DD._`
   Neutral wording, no claims that are not in the daily files.
9. Commit and push:
   ```
   git add daily/$DATE.md seen.json README.md
   git commit -m "Daily brief $DATE: N new items"
   git push origin main
   ```
   If the push is rejected as non-fast-forward, run
   `git pull --rebase origin main` and push again. Confirm with
   `git log origin/main -1 --oneline` that your commit is on the remote.
10. End your final message with exactly one of:
    - `Run complete: N new items · sources ok X/Y · pushed <short sha>`
    - `Run FAILED: <one-line reason>` (for example every source failed and
      WebSearch returned nothing usable, or the push was refused). Still commit
      whatever you produced and describe the problem in the run report.

### Standards

- Neutral, factual tone. Describe what happened and who said it. Do not take
  sides, speculate, or use loaded adjectives. Attribute claims to the outlet or
  official who made them.
- Original summaries only. No copied sentences and no quotes beyond a few
  words. Headlines may be reproduced.
- Every bullet has a working link to a named outlet. No bullet without a
  source.
- Balance: when the day's coverage is one-sided, say in the run report that the
  brief reflects what the sources carried.
- Non-English items from GDELT: put an English headline in bold and mark the
  language, for example `(fr)`.
- Keep going when a source fails and report it. Do not edit
  `routine/sources.json` or anything in `scripts/`. If a source has failed
  three days running, say so in the run report so a person can remove it.
- Do not install packages, do not touch `.github/`, and do not run anything
  that would need approval.
