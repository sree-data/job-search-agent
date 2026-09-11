# Pipeline conventions

jobs.csv status: new, pursuing, applied, skipped, closed
contacts.csv type: recruiter, hiring_manager, engineer, alumni, referral
outreach.csv channel: linkedin_note, linkedin_message, email
outreach.csv touch: 1 (first), 2 (follow-up 1), 3 (follow-up 2). Stop after 3.
outreach.csv status: draft, approved, sent, replied, no_reply, closed
followup_due: sent_date + 5 days for touch 2, + 12 days for touch 3

Alex edits status from draft to approved. The agent moves it to sent only after the email actually goes out.
