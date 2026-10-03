# prayer/

One prayer guide per day, in three formats with the same content:

- `YYYY-MM-DD.md`: Markdown, readable on GitHub
- `YYYY-MM-DD.docx`: Microsoft Word
- `YYYY-MM-DD.pdf`: PDF, A4

The routine writes them after the day's news brief (`daily/YYYY-MM-DD.md`).
They are built by `scripts/build_prayer.py` from a short spec the routine
writes. The script inserts the exact King James Version text from
`data/kjv.tsv.gz`, so Scripture is never quoted from memory.

## Structure (10 points)

| Part | Points | What it prays about | Scripture |
|---|---|---|---|
| 1 | 1–5 | Issues in that day's news brief, each linked to its stories | Old and New Testament both present |
| 2 | 6–8 | Divine protection of the nation of Israel and of Jews everywhere | Old and New Testament both present |
| 3 | 9–10 | Salvation of Jewish people: coming to faith in Jesus as Messiah and Lord | One Old, one New Testament |

Each point has a short focus line, the KJV passage (1–4 verses) with its
reference and testament, and a prayer. The guide opens with Romans 10:1 and an
"At a glance" list, and ends with a closing prayer.

## How the prayers are written

- **To the Lord Jesus, by name**, in the first person ("Lord Jesus, I ask
  You…"), so the reader can pray them as written.
- **Grounded in the passage**: pick up its words and promises.
- **Specific to the news**: name the places, communities and needs in the
  story, but keep facts to what the brief reports.
- **Bless and intercede; never curse.** Pray for protection, peace, comfort
  for the grieving, wisdom for leaders, justice, and the restraint of those
  who plan violence. Never call down harm on any person or people
  (Matthew 5:44; Romans 12:14). Where a story involves suffering on more than
  one side, it is fitting to pray for all the innocent.
- **Salvation prayers** ask that Jewish people come to know Jesus as Messiah
  and Lord, with the love of Romans 10:1 and 9:1-3, never with contempt.
- **No politics as fact.** Pray about decisions and outcomes without
  presenting a political position or prediction as certain.
- **60 to 140 words** per prayer (the script enforces 35–200), and a closing
  prayer of 40 to 90 words.

## Rules the build script enforces

- Exactly 5 + 3 + 2 points, with Old and New Testament both present in each part.
- Every reference exists in the KJV, is 4 verses or fewer, and does not stop
  mid-sentence.
- No passage is used twice in a guide or in the previous 7 days' guides.
- Every prayer names the Lord Jesus.
- Part 1 points link to stories in that day's brief.

## Making or fixing a guide by hand

```bash
python3 scripts/build_prayer.py --example > .brief/prayer.json   # template
python3 scripts/bible.py "Psalm 121:3-4"                         # check a passage
python3 scripts/bible.py --search "keepeth Israel"               # find one
python3 scripts/build_prayer.py .brief/prayer.json --check       # validate only
python3 scripts/build_prayer.py .brief/prayer.json               # write md, docx, pdf
```

See `scripture-bank.md` for verified passages by theme.

## Scripture text

The King James Version (1769 text) is in the public domain. The bundled text
in `data/kjv.tsv.gz` was built by majority vote across five public-domain
digital editions (eBible.org, aruljohn/Bible-kjv, thiagobodruk/bible,
scrollmapper/bible_databases, bibleapi/bibleapi-bibles-json), which removes the
typos and modernised spellings that each edition has on its own.
