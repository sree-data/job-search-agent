# outreach-engine

The decision core for a job-search cold-outreach product. See `ARCHITECTURE.md` for the why; this file is the how.

```
pip install -e ".[dev]"
pytest
```

## Quick tour

```python
from datetime import date, datetime
from zoneinfo import ZoneInfo
from outreach_engine import *
from outreach_engine.models import Sponsorship, ContactType, Channel
from outreach_engine.sequence import Thread

me = Candidate(id="alex", skills={"sql","python","snowflake","power bi","azure"}, years_experience=4,
               target_titles=["data engineer"], target_locations=["phoenix","tempe","remote"],
               needs_sponsorship=True, industries=["health","tech"],
               facts={"migrated business objects reporting to power bi for a health system"})

jobs = [Job("j1","Lakeside Health System","Data Engineer II","sql snowflake azure pipelines","Phoenix, AZ",date(2026,9,9),
            industry="healthcare", sponsorship=Sponsorship.YES, company_sponsor_history=True),
        Job("j2","BigBank","Senior Data Architect","spark scala","New York, NY",date(2026,8,1), industry="finance")]

ranker = JobFitRanker()
for job, score, contrib in ranker.rank(me, jobs):
    print(f"{score:.2f}  {job.company:14} {job.title:26} {ranker.explain(contrib)}")

contacts = [Contact("c1","j1","A. Patel","Manager, Data Platform",ContactType.HIRING_MANAGER, has_public_activity=True, role_relevance=0.9),
            Contact("c2","j1","R. Gomez","Technical Recruiter",ContactType.RECRUITER, has_email=True, role_relevance=0.6),
            Contact("c3","j1","K. Reddy","Data Engineer",ContactType.ALUMNI, shared_hook="ESU alum", role_relevance=0.5)]
print([c.name for c in ContactPrioritizer().pick(contacts, k=2)])   # alumni first, then hiring manager

gate = MessageQualityGate()
draft = Message("c3", Channel.LINKEDIN_MESSAGE, "", "Hope this finds you well! I'm reaching out about any opportunities...", claims=set())
print(gate.check(draft, me).reasons)   # every reason the draft was rejected

seq = SequenceEngine()
t = Thread("t1","alex","c2","Lakeside Health System",Channel.EMAIL, recipient_tz="America/Phoenix")
seq.approve(t)
print(seq.next_send_slot(t, datetime.now(ZoneInfo("America/Phoenix"))))
```

## Plugging in a model

`generation.generate()` takes any `call(prompt) -> str`. Wrap the Anthropic Messages API (or anything else) and pass it in. The gate loop handles retries and refuses to return a failing draft.

## What to replace as you scale

- `JobFitRanker._text_sim` → embeddings
- `Outcome` rows → a real table; call `fit()` nightly per cohort, per user once they have 30+ applied outcomes
- `SequenceEngine._sent_log` → the threads table; caps become queries
- Priors in `contacts.py` → your measured rates
