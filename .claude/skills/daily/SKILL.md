---
name: daily
description: The scheduled daily run. Finds new jobs, researches the top ones, finds contacts, drafts outreach, checks for replies and follow-ups, and writes a summary Alex can read in two minutes.
---

# Daily run

This runs unattended. It never sends anything to anyone but Alex. It reads, researches, drafts, and
logs, and it has exactly one send permission:

**The self-send exception.** After writing `pipeline/daily-summary.md`, run

    python3 scripts/build_daily_report.py

It reads the summary plus the pipeline CSVs and today's draft files and writes `daily-email.html`,
`job-search-<date>.pdf`, `job-search-tracker-<date>.xlsx` and `report-meta.json` into
`pipeline/report/`. It then copies the PDF and the tracker into the iCloud Drive folder
`~/Library/Mobile Documents/com~apple~CloudDocs/JobSearch/`, links them from the HTML body, and
deletes generated reports there older than 30 days. Do not hand-build any of the three files.

Then email it to `alex.rivera@example.com` and no one else, with `htmlBody` set to the
contents of `daily-email.html`, `body` set to the plain markdown summary as the text alternative,
and subject `Job search daily — <date>`.

**Do not attach anything.** The PDF and the tracker reach Alex through iCloud Drive, and the email
links to them. Attaching would mean inlining about 40KB of base64 into the send call, which is what
made an earlier run drop the files silently. If `report-meta.json` shows `published` empty, say in
the email that the files could not be written to iCloud and give their paths under `pipeline/report/`
instead.

That single address is the entire exception. A `PreToolUse` hook (`scripts/guard-gmail-send.py`)
enforces it and will deny any send that names another recipient, including one added in cc or bcc.

Outreach to a contact never goes out here, in any channel. LinkedIn drafts are pasted by Alex
himself. Email to a contact goes only through `/send-email`, only for a draft Alex has marked
`approved`, and only with Alex present. If the summary email fails to send, say so in the log and
carry on; the summary file is still the record.

1. Run `/followups` first, in reply-check mode: look for Gmail replies to sent emails and update the pipeline. Draft due follow-ups.
2. Run `/find-jobs`.
3. Take the top 3 new jobs by score. For each: `/research-company`, then `/find-contacts`, then `/draft-outreach` for the single best contact. Stop at 10 total drafts for the day.
4. Write `pipeline/daily-summary.md` (overwrite it) with, in this order:
   - Replies received (name, company, one-line gist). If any, put "You have replies" as the first line.
   - Follow-ups drafted and waiting for approval.
   - New roles found today, top 5 with score and link.
   - New outreach drafted, **in full**. Alex reads and copies these on his phone, so never make him
     open a file. For each draft give, in this order:
     - person's name and title, company, and the job id
     - the LinkedIn connection note, verbatim, in its own fenced code block
     - the LinkedIn message, verbatim, in its own fenced code block
     - the cold email, verbatim, subject line included, only if one was written
     - the send date and the local time window, with the time zone named
     - any pre-send check on one line: a title to confirm, a req to apply to first
     Put the draft file path on the last line, for reference rather than as the way in. Still write
     the draft file and still log its row in `pipeline/outreach.csv` as usual.
   - Anything that needs Alex's input: contacts you couldn't identify, claims you weren't sure you could make, a posting that looked good but had a sponsorship question.
   - Pipeline counts: roles pursuing, messages out, awaiting reply, replies this week.
5. Keep everything except the drafts under 40 lines. The verbatim drafts are exempt from that
   limit: never truncate, paraphrase, or summarise a draft to save space. No preamble.
