---
name: draft-outreach
description: Write the LinkedIn connection note, LinkedIn message, and cold email for one contact, in Alex's voice, and log them as drafts. Usage /draft-outreach <contact id>
---

# Draft outreach

Argument: a contact id from `pipeline/contacts.csv` (or a name if the id is unknown).

Before writing, read: `CLAUDE.md` writing rules and audience angles, `profile/background.md`, `profile/resume.md`, `profile/voice-samples.md`, the contact's row and its `shared_hook`, the linked job row, and `drafts/research/<company>.md` if it exists (run `/research-company` first if it doesn't).

Write three pieces to `drafts/<contact-id>-<lastname>.md`:

## A. LinkedIn connection note (under 200 characters)
One sentence. The hook, then why you want to connect. No pitch.

## B. LinkedIn message (60 to 100 words)
For after they accept, or as an InMail. Structure: hook about them (1 sentence) → one proof point about Alex that matches (1 to 2 sentences) → one small ask (1 sentence). Sign off with just "Alex".

## C. Cold email (under 120 words)
Subject line under 7 words, specific. Same structure as B but can carry one extra detail. Include Alex's LinkedIn URL in the signature. Only write this if the contact has a published email or Alex says he has one.

Then, under the drafts, add:
- **Why this angle**: two lines on what you anchored to and which proof point you chose.
- **Sponsorship**: whether you mentioned it, per `targets/criteria.md`, and if so where.
- **Send timing**: best day and time in the contact's time zone (Tuesday to Thursday, 8 to 10am local is a safe default).

Finally, append one row per piece to `pipeline/outreach.csv` with touch `1`, status `draft`, and the draft file path.

Self-check before you save. Rewrite if any of these are true:
- The first sentence is about Alex instead of them.
- It contains a banned phrase from `CLAUDE.md`.
- It claims something not in `profile/`.
- It would work unchanged for a different person at a different company. That means it's a template, and templates get ignored.
- It sounds more polished than the voice samples. Rough and specific beats smooth and generic.
