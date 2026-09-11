---
name: research-company
description: Build a short company brief for outreach and interview prep. Usage /research-company <company name>
---

# Research company

Argument: company name (or a job id from pipeline/jobs.csv).

Use web search and web fetch. Spend at most 6 to 8 searches. Write the brief to `drafts/research/<company-slug>.md` and print it.

Cover, in this order, each in two or three lines:
1. What they do and roughly how big the data/engineering org is.
2. Data stack. Look at their engineering blog, job postings, conference talks, GitHub, and tech-stack sites. Name the actual tools (Snowflake, Databricks, Azure, dbt, Airflow, Power BI, etc.). Mark anything unverified as such.
3. Recent news that a data engineer would care about: a migration, a platform build-out, an acquisition, a new product, layoffs or hiring pushes.
4. Sponsorship: any public evidence they sponsor H1B (public disclosure data, their own postings, Glassdoor-style reports). Say "no evidence found" if none.
5. Hooks: three specific things Alex could reference in a message. A named project, a talk by a named engineer, a blog post, a public problem they've described. Each hook needs a URL.
6. Fit: one honest line on why Alex is or isn't a good match, based on `profile/background.md`.

Do not make anything up. If a section has nothing verifiable, say so in one line and move on.
