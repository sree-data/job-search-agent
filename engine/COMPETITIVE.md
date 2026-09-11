# Competitive map (September 2026) and where this engine is ahead

## The field

**Auto-apply agents** — Sonara, LazyApply, LoopCV, JobRight, AIApply, JobCopilot, Sorce, Tsenta, Resumly, JobHire.ai, RJA.
Sell volume: 40–1,500 applications a day. Independent testers report 2–3% response rates as "normal" for volume applying, Trustpilot scores in the 2–4 range for several, and structural delivery-verification problems because they submit to aggregated listings rather than the company's page. Two carry BBB F ratings. The tools that tailor per application (JobRight, Resumly, JobHire) do better on quality but still measure success as applications sent.

**LinkedIn automation** — Expandi, Dripify, Waalaxy, We-Connect, LinkedFusion.
Sales tools repackaged for job seekers. Personalization is merge tags (first name, company, title). All of them run automated actions against LinkedIn, which is exactly what gets accounts restricted; the Chrome-extension variants in the auto-apply space carry the same exposure.

**Outreach drafting** — Jobply cold email, LoopCV recruiter email finder, JobRight "insider referrals", Careerflow, Teal, Huntr.
One-click draft from resume + job description + company page. No quality gate, no claim verification, no learning loop, no cross-user coordination. Teal and Huntr are good trackers and don't pretend otherwise.

## What every one of them lacks, and what this engine does instead

| Gap in the market | Module | What it does |
|---|---|---|
| Personalization = merge tags | `hooks.py` | Mines rare, recent, sourced facts about the reader; ranks by type prior × specificity (IDF across everything mined) × freshness; boosts things the reader wrote themselves; refuses hooks with no URL |
| No quality bar before sending | `quality_gate.py` | Length, opens-with-them, hook present, every claim verified against the user's facts, template similarity vs recent sends, banned phrases. Fails closed. |
| No learning from replies | `bandit.py` | Thompson sampling over (hook kind × proof point × ask) per cohort, rewards replies and interviews, new cohorts inherit global beliefs |
| Optimizes applications, not interviews | `planner.py` | Spends the user's daily budget on expected interviews = job fit × P(reply) × P(interview \| reply), with reasons per item |
| Users of the same product collide on the same recipient | `planner.RecipientLedger` | Global weekly cap per recipient across all tenants |
| A reply is treated as one thing | `replies.py` | Interested / redirect / not-now / rejection / auto-reply / bounce, each with a defined next action; bounces feed the suppression list |
| LinkedIn automation risk | `sequence.py` | LinkedIn is structurally unsendable by the system; copy-and-send UX; caps per day and per company |
| Black-box match scores | `ranking.py` | Linear, explainable, priors on day one, learns per user from applied → interview outcomes with shrinkage |

## What this does not do, on purpose
- Auto-apply. Fourteen thousand applications in your name is a reputational event, not a strategy.
- Send on LinkedIn.
- Guess email addresses.
- Claim anything about the user that isn't in their verified facts.

## What decides whether it's actually better
Reply rate per first touch and interviews per ten messages, measured on real users, against the 2–3% volume baseline and the 15–25% fully-personalized human baseline that practitioners report. The engine is built to move those two numbers and to prove it with its own logs. Until there are logs, "best" is a design claim.
