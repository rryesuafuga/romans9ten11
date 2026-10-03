# Running the daily brief as a Claude Code routine

This repository is set up so that a **Claude Code routine** (Anthropic's cloud,
no computer of yours switched on) runs every day at **03:07 Uganda time
(EAT, UTC+3), which is 00:07 UTC**, gathers the last ~30 hours of world news on
Israel, Jews in Israel, Judea and Samaria and the Jewish diaspora, and commits
a dated brief plus a rolling 7-day summary to `main`.

Status of the feature (checked against the Claude Code docs on 3 October 2026):
routines are a *research preview*, available on Pro, Max, Team and Enterprise,
billed against your subscription like any Claude Code session. Behaviour and
limits may change, so expect to watch the first week of runs.

## What is in the repo

| Path | Role |
|---|---|
| `routine/PROMPT.md` | The routine's instructions. Paste the *short prompt* into the routine; the run reads the full text from the repo. |
| `routine/sources.json` | Google News RSS queries, GDELT queries and curated outlet feeds the fetch script pulls. |
| `scripts/fetch_candidates.py` | Pulls every source, filters to the time window, drops stories already in `seen.json`, writes `.brief/candidates.json` for Claude to triage. Standard library only. |
| `scripts/mark_seen.py` | After the brief is written, records its links in `seen.json` (pruned to 60 days). |
| `daily/README.md` | Format rules and template for a daily file. |
| `daily/YYYY-MM-DD.md` | One brief per run, written by the routine. |
| `seen.json` | URLs and headline fingerprints already covered. |
| `README.md` | Carries the rolling summary between two HTML comment markers; the routine rewrites only that block. |

The scripts were tested offline with sample feeds (dedupe by URL and by
headline, failing sources reported without aborting, exit code 2 when every
source fails). They were **not** run against the live feeds, because the
sandbox that produced them has the default network policy, which blocked every
news host. That is the same block your routine will hit unless you do step 2.

## 1. Get the scaffold onto `main`

Routines clone the repository's default branch. Merge the branch
`claude/magical-ritchie-1miwwo` into `main` (open a pull request on GitHub, or
locally `git checkout main && git merge claude/magical-ritchie-1miwwo && git push`).
Check that `main` now shows `SETUP.md`, `routine/`, `scripts/`, `daily/` and
`seen.json`.

If `main` has branch protection that forbids direct pushes, either relax it for
this repository or change the prompt to push to a fixed branch such as
`brief` and read the briefs there. The routine cannot approve its own pull
requests.

## 2. Create a cloud environment with Custom network access

Why: the default environment ("Trusted") only allows package registries,
GitHub, cloud SDKs and a few developer domains. When this scaffold was built,
all 21 news hosts tested from such an environment were refused with HTTP 403
by the proxy. Claude's built-in WebSearch still works there, because it goes
through Anthropic's API, but the fetch script needs direct access to the feeds.

1. Open <https://claude.ai/code>, go to **Environments** (or, from inside any
   cloud session, the environment menu in the title bar, then **Edit**).
2. Create a new environment, for example `news-brief`.
3. **Network access** → **Custom**. Keep the default list of package managers,
   then add these allowed domains (the second form covers the `www.` host where
   the feed lives there):

   ```
   news.google.com
   api.gdeltproject.org
   timesofisrael.com        www.timesofisrael.com
   jpost.com                www.jpost.com
   haaretz.com              www.haaretz.com
   israelhayom.com          www.israelhayom.com
   ynetnews.com             www.ynetnews.com
   972mag.com               www.972mag.com
   jta.org                  www.jta.org
   forward.com
   jewishnews.co.uk         www.jewishnews.co.uk
   feeds.bbci.co.uk
   aljazeera.com            www.aljazeera.com
   theguardian.com          www.theguardian.com
   ```

   If you would rather not maintain a list, choose **Full** access instead. It
   is simpler but lets the run reach any host.
4. Leave the setup script empty. The scripts need only Python 3, which the
   cloud image already has.

Docs: <https://code.claude.com/docs/en/cloud-environments#network-access>

## 3. Create the routine

Pick one of the three ways.

**A. Web UI (recommended).**

1. Go to <https://claude.ai/code/routines> → **New routine**.
2. Repository: `rryesuafuga/romans9ten11`. Environment: the one from step 2.
3. Trigger: **Schedule → Daily → 03:07**. Times are entered in your local zone
   and converted to UTC automatically, so make sure the browser you are using
   is set to Africa/Kampala. Uganda has no daylight-saving time, so the UTC
   value never drifts. Avoid 03:00 exactly: the docs warn that on-the-hour runs
   can start several minutes late.
4. Prompt: paste the **short prompt** from `routine/PROMPT.md`.
5. Model: the most capable model your plan offers for the best triage and
   summaries; Sonnet is the economical choice if usage matters more. The
   selected model is used on every run.
6. Connectors: none are needed. Everything goes through git and public feeds.
7. Create it. The detail page shows the next run time; confirm it reads
   03:07 EAT (00:07 UTC).

**B. From the CLI.** In any Claude Code session on this repo type `/schedule`
and describe the routine in plain words ("every day at 03:07 Africa/Kampala,
follow routine/PROMPT.md…"). `/schedule update` lets you set the cron directly;
the UTC form is `7 0 * * *`.

**C. From this Claude Code session.** Ask Claude to create it: the session has
the routine-creation tool and can set
`CRON_TZ=Africa/Kampala 7 3 * * *` with a fresh session per run. Say which
model you want.

Permissions: routine runs are fully autonomous. There is no permission-mode
picker; shell commands and git run without approval. That is what makes
unattended operation possible, and it is also why the prompt confines the run
to three files.

## 4. First run: press "Run now" and check five things

1. The run list shows green. Remember the docs' caveat: green means the
   session started and exited without an infrastructure error, **not** that the
   task succeeded. Open the run and read the transcript.
2. `main` has a new commit `Daily brief YYYY-MM-DD: N new items`.
3. `daily/YYYY-MM-DD.md` exists, follows the template, and ends with
   `Run complete: N new items · sources ok X/Y …`.
4. In that run report, look at the failed sources. Anything with `HTTP 403`
   or `URLError` is almost always a domain missing from the environment's
   allowed list. Add it and run again. Feeds marked `"unverified": true` in
   `routine/sources.json` were never reached from the sandbox; if one fails on
   three consecutive days, delete it from the file.
5. `seen.json` has entries and the README's rolling summary is no longer the
   placeholder.

"Run now" counts toward a limit of 30 manual fires per routine per hour, which
you will not hit in normal use.

## 5. The first week

- Each morning, open <https://claude.ai/code/routines> and the repo. A missing
  `Run complete` line, or a day with no commit, is a failed run; read the
  transcript.
- Scan a few bullets against their links for accuracy and tone. Tighten
  `routine/PROMPT.md` if the brief drifts (too long, editorialising, duplicate
  stories). Edits to the file take effect on the next run without touching the
  routine, because the short prompt tells the run to read the file.
- Quiet days produce short files. That is expected; the file still exists.
- If the GitHub connection lapses, runs are skipped for up to 72 hours and
  then the routine switches itself off. Reconnect GitHub at claude.ai/code and
  re-enable it.

## 6. When something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Run report says every source failed; exit code 2 | Environment is still Trusted, or domains missing | Step 2; re-run |
| One or two feeds fail every day | Feed URL changed or outlet blocks bots | Remove or replace the entry in `routine/sources.json` |
| Green run, no commit on `main` | Push refused (branch protection) or Claude stopped early | Read the transcript; relax protection or switch to a fixed branch |
| Brief created on a `claude/…` branch | Prompt was shortened and lost the "push to main" rule | Restore the short prompt from `routine/PROMPT.md` |
| Same story appears two days running | Outlet changed the URL and headline | Normal in small numbers; dedupe is by URL and by the first 12 words of the headline |
| Two files for one day, or a duplicate section | Re-run on the same date appended instead of rewriting | The prompt says rewrite; delete the duplicate once and watch the next run |
| Run starts 5–10 minutes late | Scheduler load at the top of the hour | Expected; 03:07 already avoids the worst of it |
| Routine shows disabled | GitHub connection lapsed for 72 h, or you paused it | Reconnect, then enable |

## 7. Usage and cost

Each run is a normal Claude Code cloud session billed to your subscription.
Expect one run a day of roughly 10–25 minutes: a few file reads, two script
runs, 4–8 WebSearch calls (one call may issue up to eight backend searches;
a session is capped at 200 calls), one commit. Google News RSS and GDELT are
free and need no key. If you move to an API key later (for example the GitHub
Actions fallback below), web search on the API costs $10 per 1,000 searches on
top of tokens.

## 8. Fallback if routines misbehave: GitHub Actions

The same prompt and scripts work from a scheduled GitHub Actions workflow with
`anthropics/claude-code-action@v1`, authenticated with `ANTHROPIC_API_KEY` or a
`CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`, stored as repository
secrets. Sketch (untested here; do not add it while the routine is also
running, or you will get two briefs a day):

```yaml
name: daily-brief
on:
  schedule:
    - cron: "7 0 * * *"      # 03:07 Africa/Kampala, no DST
  workflow_dispatch:
permissions:
  contents: write
jobs:
  brief:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: "Open routine/PROMPT.md and follow the section 'Full instructions' exactly."
          claude_args: "--max-turns 60"
```

GitHub notes: schedules run only from the default branch; midnight UTC is a
high-load slot where queued jobs can be delayed or dropped; in a public
repository, scheduled workflows are disabled after 60 days without activity
(daily commits count as activity).

## 9. Changing the scope later

- **Sources:** edit `routine/sources.json`. Google News queries use the
  `when:1d` operator; GDELT queries are `(term OR "phrase")` groups. Set
  `"filter": true` on broad feeds so `relevance_terms` is applied.
- **Themes, length, tone:** edit `routine/PROMPT.md` and `daily/README.md`.
- **Time:** edit the routine's schedule in the UI (local time) or via
  `/schedule update` (cron, UTC).
- **Window:** the prompt passes `--hours 30` so a late start never leaves a
  gap; the dedupe step stops the overlap from producing repeats.

## What this does not cover

- Notifications on completion or failure are not documented for routines.
  The daily commit (or its absence) is the signal; the first-week check is
  the safety net.
- A Google Doc or Claude artifact as the living document. The repo is the
  store here because git gives history, diffs and an unattended write path.
  If you also want a Doc, add a Google Docs connector to the routine and a
  step to the prompt; connector writes run without prompts in routines, but
  that path was not tested.
