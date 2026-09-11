---
name: followups
description: Find outreach that is due for a follow-up, check Gmail for replies first, and draft the follow-up message
---

# Follow-ups

1. Read `pipeline/outreach.csv`. Find rows with status `sent` where `followup_due` is today or earlier and `touch` is less than 3.
2. For email rows, search Gmail for a reply from that contact since `sent_date`. If one exists, set status `replied`, paste a one-line summary of the reply into `reply`, and skip drafting. Flag it to Alex at the top of your output; replies are the priority.
3. For LinkedIn rows, ask Alex whether they replied. He's the only one who can see that.
4. For rows still unanswered, draft the next touch:
   - Touch 2 (5 days after touch 1): 2 to 3 sentences. Reply in the same thread. Add one new piece of value: a relevant thing Alex built, a link to something they'd find useful, or a sharper version of the ask. Never "just following up" or "bumping this".
   - Touch 3 (12 days after touch 1): 2 sentences. Close the loop politely, leave the door open, no ask. This is the last message.
5. Save each draft to the contact's existing draft file under a "Follow-up N" heading. Append a new row to `outreach.csv` with the next touch number and status `draft`. Set the original row to `no_reply` once touch 3 has been sent.
6. Print: replies found, follow-ups drafted, threads closed.
