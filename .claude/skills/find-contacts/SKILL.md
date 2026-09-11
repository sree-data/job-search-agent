---
name: find-contacts
description: Identify the recruiter, hiring manager, team engineers, and any alumni or shared connections for a target company or job. Usage /find-contacts <company or job id>
---

# Find contacts

Argument: company name or job id.

Goal: 3 to 5 named people worth contacting for this role, with a reason for each. Save them to `pipeline/contacts.csv`.

How to find them (web search and web fetch only; do not use any browser tool on linkedin.com):
- Recruiters: search "<company> technical recruiter" or "<company> talent acquisition data". Job postings sometimes name the recruiter. Company career pages sometimes list them.
- Hiring managers: search "<company> data engineering manager", "<company> director data platform". Engineering blog authors and conference speakers are often the manager or a senior on the team.
- Team engineers: authors of the company's data engineering blog posts, speakers at Snowflake/Databricks/Azure events, maintainers of the company's public repos.
- Alumni: search "<company>" together with "Example State University", "ESU", "Fabrikam Motors", "Contoso Analytics", "Northwind Health". Shared employer or school is the hook. If Alex has told you about other shared things (hometown, undergrad school), use those too.

For each person record: name, title, type, LinkedIn URL if a public search result shows one, work email only if it is published somewhere (never guess an email pattern), where you found them, and the `shared_hook` — the one specific reason this person is worth writing to.

Priority order for who to write first: alumni or referral with a real shared hook > hiring manager for the exact team > engineer on the team > recruiter. Say which one you'd start with and why.

If you can't find anyone with confidence, say so. Alex can look them up on LinkedIn himself and paste the details into contacts.csv.
