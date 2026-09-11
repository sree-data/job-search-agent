# Candidate background — EXAMPLE, replace with your own

Everything the agent is allowed to claim about you lives here. If a fact is not in this file or in
`resume.md`, the agent will not put it in a message. That rule is enforced in `CLAUDE.md` and, for
generated drafts, by `MessageQualityGate` in the engine.

The candidate below is fictional. Replace every line.

Name: Alex Rivera
Email: alex.rivera@example.com — used in email signatures
Phone: +1 555-0142
Location: Denver, Colorado. Open to relocating.
Job search scope: anywhere in the United States, remote or on-site. Preferred: Denver, Austin.
Education: M.S. Information Systems, Example State University.
Experience: 4 years as a data engineer across Lakeside Health System, Northwind Health,
Contoso Analytics and Fabrikam Motors. Healthcare, automotive, consulting.
Target: data engineer roles, healthcare first, then general tech.

## Which proof point to pick

One per message, matched to the posting's stack. Put the strongest and most specific first, and say
here which bullets to prefer and which to hold back. The agent follows this ordering literally.

## Proof points

Data quality and reconciliation — Lakeside Health System
- Cut downstream data quality incidents 90% with a parameterized crosswalk-join framework across 9 source tables.
- Wrote a Python and SQL reconciliation framework validating parity across 200+ entities and 1,000+ columns.

Healthcare data at scale — Northwind Health
- Processed 2M+ claims and member records daily in PySpark and Airflow, with SLA monitoring.
- Built ingestion for EDI 837/835 claims, provider and member data into a cloud warehouse.

Platform and streaming — Contoso Analytics
- Generated Airflow DAGs programmatically from a Python service, cutting scheduling overhead 80%.
- Built Kafka to Spark Structured Streaming ingestion, containerized, 90% test coverage.

Very large scale — Fabrikam Motors
- Tuned Spark SQL and cluster resources on a 15 TB dataset: 20% faster, 15% cheaper.

## Stack

Lead with these, in rough order of how often the market asks for them:

SQL · Python · AWS · Azure · Databricks · PySpark / Spark · Snowflake · Power BI · Airflow ·
Terraform · Amazon Redshift · Docker, Kubernetes, Git, CI/CD

## Things NOT to say
- Don't claim any tool that is not listed above. If it isn't here, ask before writing it.
- List anything you are explicitly not willing to claim, and why.
