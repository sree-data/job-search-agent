---
name: send-email
description: Send cold emails that Alex has approved in pipeline/outreach.csv, via Gmail, and log the sends
---

# Send approved emails

1. Read `pipeline/outreach.csv`. Select rows where `channel` is `email` and `status` is `approved`. If there are none, say so and stop.
2. For each row, open the draft file, show Alex the recipient, subject, and body, and ask for a single confirmation for the batch. Do not send anything before he confirms in this session.
3. Respect the daily cap of 10 emails. If the batch is larger, send the 10 with the highest job score and tell him what's left.
4. Send via the Gmail connector, one at a time, from Alex's account. Plain text. No attachments unless the row's notes say to attach the resume.
5. After each successful send, update the row: status `sent`, `sent_date` today, `followup_due` = today + 5 days. If a send fails, leave the row as `approved` and note the error.
6. Create a Google Calendar reminder on the `followup_due` date titled "Follow up: <name> at <company>", if the calendar connector is available.
7. Print a summary: sent, failed, remaining.

Never send LinkedIn messages. Never send an email whose status is `draft`. Never change `draft` to `approved` yourself.
