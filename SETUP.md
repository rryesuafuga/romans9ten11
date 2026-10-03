# Daily news brief and prayer guide: how it runs

A **Claude Code routine** in Anthropic's cloud runs every day at
**03:07 Uganda time (00:07 UTC)**, with no computer of yours switched on. Each
run:

1. gathers the last ~30 hours of world news on Israel, Jews in Israel, Judea
   and Samaria and Jewish diaspora communities, and writes `daily/YYYY-MM-DD.md`;
2. writes a 10-point prayer guide to the Lord Jesus from that news, with a
   King James Version passage and a prayer for each point, as
   `prayer/YYYY-MM-DD.md`, `.docx` and `.pdf`;
3. commits both straight to `main` (brief first, then guide).

Routines are a research preview, billed to your claude.ai subscription like
any Claude Code session. Behaviour and limits may change, so watch the first
week of runs.

## The routine

| Setting | Value |
|---|---|
| Name | Israel daily news brief + prayer guide (03:07 EAT) |
| Routine ID | `trig_01QgPz7yXwnDBAADVEVqdqGx` |
| Schedule | `CRON_TZ=Africa/Kampala 7 3 * * *` (daily 03:07 EAT; Uganda has no daylight saving) |
| How a run starts | The routine wakes the **dispatcher** session, which starts one fresh **worker** session with this repository attached and push access to `main` |
| Dispatcher | session "romans9ten11 daily dispatcher (do not archive)", Haiku 4.5, only starts the worker |
| Worker | session "romans9ten11 daily brief + prayer guide", Sonnet 5.5 (chosen to keep daily usage economical), follows `routine/PROMPT.md` |
| Environment | **Default** |
| Notifications | the worker sends its final `Run complete` / `Run FAILED` line as a push notification |

**Why a dispatcher.** A routine created from a Claude Code session cannot
attach a repository, so its runs can read the public repo but cannot push.
The first test run on 3 October hit exactly that (`403 ... not in this
session's authorized repository set`). A session started with
`create_session` can attach the repository with push access to `main`, and
the dispatcher does that each day. The second test run, started the same way,
pushed the 4 October brief and guide to `main`.

**Do not archive or delete the dispatcher session.** The routine delivers its
daily message to it. If it is gone, ask Claude to create a new dispatcher and
point the routine at it, or create the routine from
<https://claude.ai/code/routines> with this repository attached and the
worker prompt from the routine.

You can pause the routine, press **Run now**, or change the time from your
routines list at <https://claude.ai/code/routines>. The worker's model is set
inside the routine's prompt (`model: claude-sonnet-5-5`); change that line to
use a different model.

To change what a run does, edit `routine/PROMPT.md` (the full instructions),
`prayer/README.md` (how prayers are written) or `daily/README.md` (brief
format) and push to `main`. The next run picks up the change.

## What is in the repository

| Path | Role |
|---|---|
| `routine/PROMPT.md` | The run's full instructions: Phase A news brief, Phase B prayer guide. |
| `routine/sources.json` | Google News RSS queries, GDELT queries and curated outlet feeds. |
| `scripts/fetch_candidates.py` | Pulls every source, keeps the time window, drops stories already in `seen.json`. |
| `scripts/mark_seen.py` | Records a brief's links in `seen.json` so later runs skip them. |
| `scripts/bible.py` | Exact KJV lookup and word search from `data/kjv.tsv.gz`. |
| `scripts/build_prayer.py` | Checks the guide against the rules and writes Markdown, Word and PDF. |
| `scripts/docwriters.py`, `scripts/pdf_metrics.py` | Word and PDF writers, standard-library Python only. |
| `data/kjv.tsv.gz` | Full King James Version, 31,102 verses, public domain. |
| `prayer/README.md`, `prayer/scripture-bank.md` | Guide rules and 167 verified passages by theme. |
| `daily/`, `prayer/` | One brief and one guide (three files) per day. |
| `seen.json` | Stories already covered. |
| `README.md` | "Latest" links and a rolling 7-day summary, both rewritten by each run. |

## One thing to do: let the run reach the news feeds

The routine runs in the **Default** environment, whose network access is
**Trusted**. That level allows GitHub and package registries but blocks news
sites: every feed tested from it was refused. Web search still works, so the
brief is still written, but from fewer sources. To give the fetch script its
feeds:

1. Open <https://claude.ai/code>, then the environment menu, then **Default**,
   then **Edit**. Docs: <https://code.claude.com/docs/en/cloud-environments#network-access>.
2. Set **Network access** to **Custom**, keep the default package-manager list,
   and add these allowed domains:

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

   Choosing **Full** instead also works and needs no list.

Changing Default affects your other cloud sessions too. Custom with the
default list kept only adds hosts, so nothing that worked before stops
working.

## Checking a run

- Each run is a worker session named "romans9ten11 daily brief + prayer
  guide" in your session list, and it sends a push notification when it
  finishes.
- A green status only means the session started and exited cleanly. Read the
  last line of the run: `Run complete: …` or `Run FAILED: …`.
- On GitHub, `main` should gain two commits per day:
  `Daily brief YYYY-MM-DD: N new items` and `Prayer guide YYYY-MM-DD: 10 points`.
- The brief's `## Run report` lists failed sources. `HTTP 403` or `URLError`
  means a domain missing from the allowed list. A feed marked
  `"unverified": true` in `routine/sources.json` that fails three days running
  should be removed.
- The README's "Latest" line links the newest guide in all three formats.

## The first week

- Each morning, open the README's "Latest" links. Read a few prayers and
  check a few news bullets against their links.
- If prayers drift in length, tone or focus, tighten `prayer/README.md`. If
  the brief drifts, tighten `routine/PROMPT.md`.
- A second run on the same Uganda date, for example a manual Run now, merges
  new stories into that day's brief and rebuilds that day's guide.

## When something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Run report says every source failed | Default environment still Trusted | Do the network step above |
| One or two feeds fail every day | Feed moved or blocks bots | Remove or replace it in `routine/sources.json` |
| No commits, run says push refused (403) | Worker started without the repository attached | Check the dispatcher's reply for that day; the worker must be started with `source_url` and `outcome_branch: main`. Reconnect GitHub at claude.ai if access lapsed |
| No worker session at all | Dispatcher archived, or it did not call `create_session` | Read the dispatcher session's last reply; if it is archived, ask Claude to recreate it and repoint the routine |
| Brief committed, guide missing | Phase B failed; the run's last line says why | Re-run with Run now; the brief merges and the guide is rebuilt |
| Guide fails validation repeatedly | Rules too tight for a quiet news day | The script explains each problem; adjust `prayer/README.md` or the script's limits |
| Work landed on a `claude/` branch | Prompt was edited and lost the main-branch rule | Restore the routine prompt; merge the branch |
| Routine disabled | GitHub connection lapsed for 72 hours, or paused | Reconnect GitHub, then enable it |

## Making a guide by hand

```bash
python3 scripts/build_prayer.py --example > .brief/prayer.json
python3 scripts/bible.py "Psalm 121:3-4"
python3 scripts/bible.py --search "keepeth Israel"
python3 scripts/build_prayer.py .brief/prayer.json
```

## Scripture

All quotations are from the King James Version (1769 text), which is in the
public domain. The run never types Scripture: it picks references, and
`scripts/build_prayer.py` inserts the exact text from `data/kjv.tsv.gz`.

## Fallback: GitHub Actions

If routines misbehave, the same instructions run from a scheduled GitHub
Actions workflow with `anthropics/claude-code-action@v1` and an
`ANTHROPIC_API_KEY` secret. Do not run both, or you will get duplicate work.

```yaml
name: daily-brief-and-prayer
on:
  schedule:
    - cron: "7 0 * * *"      # 03:07 Africa/Kampala
  workflow_dispatch:
permissions:
  contents: write
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: "Open routine/PROMPT.md and follow the section 'Full instructions' exactly."
          claude_args: "--max-turns 120"
```
