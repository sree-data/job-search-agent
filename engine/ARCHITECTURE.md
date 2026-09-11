# Outreach Engine — product architecture

## What actually wins in this market

There are dozens of "AI job search" products. Most fail on one of four things, and none of them is the language model:

1. **They get users banned.** Anything that automates LinkedIn (auto-connect, auto-message, scraping while logged in) violates LinkedIn's terms, and LinkedIn enforces with account restrictions. A product that does this has a lifespan measured in months and a support queue full of locked-out users.
2. **They send templates.** Reply rates on personalized cold outreach run several times higher than on mass templates. If the personalization is a name and a company swapped into the same paragraph, recipients see it instantly and the product's aggregate reply rate collapses, which is the only number that matters.
3. **They don't close the loop.** Without tracking replies and interviews back to the specific job, contact type, and message, there is nothing to learn from. The product is as good on day 300 as on day 1.
4. **They optimize volume.** Auto-apply to 500 jobs looks like productivity. It produces zero interviews and burns the user's name at companies they'll want later.

So "world-class" here means: the best **ranking** of where a user's hours go, the best **contact selection**, a **quality gate** that refuses to ship a bad message, a **sequence engine** that behaves like a careful human, and a **feedback loop** that improves all four per user and per cohort. That's what `outreach_engine/` implements. The LLM call is a thin layer inside it on purpose.

## System

```
                  ┌────────────────────────────────────────────────────────────┐
                  │  Ingestion: licensed job feeds + user-added URLs           │
                  │  (dedupe by canonical URL + company/title hash)            │
                  └───────────────┬────────────────────────────────────────────┘
                                  ▼
   Enrichment ──────► JobFitRanker ──────► top-N per user per day (explainable scores)
   (company facts,           │
    stack, sponsor           ▼
    history, contacts)  ContactPrioritizer ──► 1–2 contacts per job, EV-ranked
                             │
                             ▼
                    Generation ⇄ MessageQualityGate  (retry with reasons, max 3, then escalate to user)
                             │
                             ▼
                    SequenceEngine ──► email via user's own Gmail OAuth (after user approval)
                             │        └► LinkedIn: "copy and send" task; user marks sent
                             ▼
                    Tracking: reply detection (Gmail thread), user-reported LinkedIn replies,
                              interview / offer events
                             │
                             ▼
                    Learning: Outcome rows → JobFitRanker.fit(), ContactPrioritizer.update_priors(),
                              generation evals (which hooks / proof points / asks get replies)
```

## Components (what's in this repo)

| Module | Decision it owns | Cold-start behaviour | Learns from |
|---|---|---|---|
| `ranking.py` | Which jobs deserve the user's time | Interpretable priors, hard gate on "no sponsorship" | Applied → interview outcomes; weights blend toward the fit as data grows |
| `contacts.py` | Who to write first | Reply-rate and interview-given-reply priors by contact type, multipliers for real hooks | Per-type observed rates, shrunk toward priors |
| `quality_gate.py` | Whether a draft can leave the building | Length, opens-with-them, specificity, claim verification, template similarity, banned phrases | Thresholds tuned against reply data |
| `sequence.py` | When to send, follow up, stop | 3 touches (0 / +5 / +12 days), Tue–Thu 8–10:30 recipient-local, daily and per-company caps, suppression list | Send-time and cadence A/B |
| `hooks.py` | Which facts about the reader to anchor on | Type prior × IDF specificity × freshness, provenance required | Which hook kinds earn replies (via bandit) |
| `bandit.py` | Which message angle to write next | Uniform Beta priors, cohorts inherit global | Replies (+1) and interviews (+3) per arm |
| `planner.py` | Where the day's budget goes | EV = fit × P(reply) × P(interview\|reply); per-company cap; cross-tenant recipient ledger | Everything above |
| `replies.py` | What a reply means and what to do next | Rules for the unambiguous cases, LLM for the rest | Label corrections from users |
| `generation.py` | The prompt and the retry loop | Structure per channel, voice samples, single hook, single proof point, single ask | Hook/proof/ask attribution to replies |

Everything the model may say about a user comes from `Candidate.facts`, which is extracted from the user's resume and confirmed by the user once. The gate rejects any claim outside that set. This is the difference between "the AI made something up about me to a hiring manager" and a product people trust.

## Multi-tenant build (what's not in this repo)

- **Auth and per-user OAuth.** Gmail send + read scopes for reply detection. Google requires an independent security assessment (CASA) to publish an app using restricted Gmail scopes; budget months and real money for it. Until then, run as an unverified app for the first ~100 users.
- **Job data.** Do not scrape Indeed/LinkedIn. License a feed (aggregators exist that sell deduplicated postings with company metadata) and let users paste URLs for anything else. Sponsorship history comes from the public H-1B disclosure data, which is free and refreshed quarterly.
- **Contact discovery.** Web search plus enrichment APIs (Apollo, Hunter, PDL and similar) for verified emails only. Never guess email patterns; a bounce costs deliverability for every user on the domain.
- **LinkedIn.** Copy-and-send UX. A browser extension that reads the page the user is on to prefill the message box is the closest you can get; injecting into LinkedIn's DOM is still a ToS risk, so ship it last and behind a warning.
- **LLM layer.** Cheap model for extraction and scoring features, strong model for drafts, batch processing overnight for company research, prompt caching for the per-user profile block. Cost is dominated by research, not drafting; cache company briefs across users.
- **Storage.** Postgres for users/jobs/contacts/threads/outcomes, object store for resumes (encrypt, delete on request), vector index for job and company text when you replace TF-IDF with embeddings.
- **Compliance.** One-to-one personal emails from a user's own mailbox; still honor opt-outs globally via the suppression list, keep a physical address in the signature, and never send from a domain you own on the user's behalf. Resume data is PII: retention policy, deletion endpoint, SOC 2 before selling to anyone who asks.

## Metrics that define "world class"

- Reply rate per first touch, by channel and contact type (target: 3× the generic-template baseline)
- Interviews per 10 messages sent
- Gate pass rate on first generation (rising means the prompt is learning; falling means the model regressed)
- Time to first interview per new user
- User-reported "this doesn't sound like me" rate
- Zero LinkedIn restrictions attributable to the product

## Sequencing the build

1. **Dogfood (now).** The Claude Code scaffold runs one user's search end to end with this engine's rules baked into the skills. Every draft, send, reply, and interview gets logged as an `Outcome`. Fifty real outcomes are worth more than any feature.
2. **Single-user web app.** Same engine, a UI, Gmail OAuth, licensed job feed. Ten users you talk to weekly.
3. **Multi-tenant.** Only once reply rate and interviews-per-message are measurably better than what users were doing by hand. If they aren't, the algorithm isn't the problem and scaling won't fix it.
