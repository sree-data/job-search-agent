---
name: find-jobs
description: Pull new data engineering postings from Dice, ZipRecruiter, and LinkedIn job-alert emails, score them against targets/criteria.md, and add the good ones to pipeline/jobs.csv
---

# Find jobs

1. Read `targets/criteria.md`, `targets/companies.md`, and `targets/market-demand.md`. Read `pipeline/jobs.csv` so you don't add duplicates (match on company + title, or URL).
2. Search Dice and ZipRecruiter for each title in criteria, nationwide and remote. Limit to postings from the last `posted_within_days`. Dice pages carry the full description in structured data; fetch them. ZipRecruiter results have no description text, so open the posting URL when one exists.
2a. Search Gmail for LinkedIn job alerts from the last 3 days, **both direct and forwarded**.
    LinkedIn sends Alex's alerts to `alex.rivera.alerts@example.com`, a separate account that he
    forwards into the connected inbox (`alex.rivera@example.com`). Note the two addresses
    differ only in the order of the name halves; they are different accounts, not a typo.
    Run all three queries:
    - `from:linkedin.com newer_than:3d`
    - `from:alex.rivera.alerts@example.com (linkedin OR "job alert" OR "jobs for you" OR "new jobs") newer_than:3d`
    - `(subject:Fwd OR subject:Fw OR "Forwarded message") ("job alert" OR "jobs for you" OR "new jobs" OR linkedin) newer_than:3d`

    All three are needed because forwarding rewrites the sender inconsistently. Gmail auto-forwarding
    usually preserves LinkedIn as the `From`, so query 1 catches it; a manual forward puts the
    forwarding account in `From`, so query 2 catches it; query 3 is the fallback for any other shape.
    Keep the content terms bound to query 2 so it matches alerts rather than everything that account
    has ever sent.

    Open each hit with `get_thread` at `PLAIN_TEXT` and pull every job URL out of the body, including
    from a quoted forward block. LinkedIn alert links appear as `linkedin.com/jobs/view/<id>` and as
    tracking links under `linkedin.com/comm/jobs/view/<id>`; normalise both to `linkedin.com/jobs/view/<id>`.
    Fetch each public posting page (allowed without logging in, per hard rule 1) and treat those
    postings exactly like job-board results.

    If these queries return nothing, say so explicitly in the step 6 output rather than staying
    silent, and name which of the three matched zero. A sender address that has never sent mail looks
    identical to a quiet week, and only the first is worth fixing.
3. For each posting, read the full description and check:
   - level, per criteria
   - sponsorship signal: `yes` if it says sponsorship available or the company has H-1B filing history; `no` if it matches any `skip_posting_if` phrase; `unknown` otherwise. Skip `no`.
   - stack overlap with `profile/background.md`
4. Score 0 to 100 using the weights in criteria, then run `JobFitRanker` from the engine and use its score as the tiebreaker. Only add postings at or above `minimum_score_to_pursue`.
5. Append each new posting to `pipeline/jobs.csv` with the next id, today's date, status `new`, and a one-line note on why it scored what it did.
6. Print a short table: id, company, title, location, score, sponsorship signal. Sorted by score. Recommend the top 3 to pursue today and say why in one line each.

If a connector is unavailable this session, run with the sources that are up rather than stopping,
and say which source was missing in the step 6 output so the day's list can be read for what it is.

Don't apply to anything. Don't pad the list. Five good roles beat thirty mediocre ones.
