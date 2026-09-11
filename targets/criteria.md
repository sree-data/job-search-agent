# Role criteria — EXAMPLE, replace with your own

Everything here is read by `/find-jobs` on every run. Scores are computed from `score_weights`, and
a posting below `minimum_score_to_pursue` is never added to the pipeline.

titles: Data Engineer, Analytics Engineer, BI Engineer, ETL Developer, Data Platform Engineer, Cloud Data Engineer
levels: entry, associate, I/II, mid. Skip anything titled Senior, Staff, Lead, Principal, Manager.
  State plainly whether this filter is deliberate, so the agent does not keep querying it.
locations: anywhere in the United States, remote or on-site. Preferred but not filtered on: Denver CO, Austin TX.
industries: healthcare first (health systems, payers, health tech), then general tech, finance, retail.
stack_bonus: SQL, Python, AWS, Azure, Databricks, PySpark, Snowflake, dbt, Airflow, Kafka, Power BI, Terraform
posted_within_days: 14

work_authorization:
  status: describe yours in one line. If you need sponsorship, say which visa and by when, because it
    changes which employers are worth pursuing at all.
  skip_posting_if: the posting says "no sponsorship", "US citizens only", "must be authorized without
    sponsorship now or in the future", or "GC/USC only".
  prioritize: companies with H-1B filing history (public disclosure data), large employers, consulting
    firms and health systems that file regularly.
  mention_in_first_message: recruiters yes, one clause near the end. Hiring managers no. Alumni no.

score_weights: title match 30, location 10, sponsorship signal 30, stack overlap 20, industry 10
minimum_score_to_pursue: 60
