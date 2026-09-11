# Job search outreach agent

A [Claude Code](https://claude.com/claude-code) project that runs a job search the way a diligent
person would: it finds roles, researches the companies and the people behind them, drafts cold
outreach in your voice, and emails you a summary every weekday morning. It never sends anything to
anyone but you.

It is not a mass-application tool. The volume caps are deliberately low, and the quality gate will
refuse a draft that reads like a template.

---

## What it actually does

Every weekday at 07:00 a scheduled run:

1. checks your inbox for replies to anything already sent, and drafts follow-ups that are due
2. pulls new postings from connected job boards and from LinkedIn job-alert emails
3. scores each posting against your criteria, dropping those that fail work-authorisation screening
4. researches the top companies, finds named people worth writing to, drafts outreach for the best one
5. writes a summary, renders it to PDF and an `.xlsx` tracker, and emails you the lot

You paste the LinkedIn messages yourself. Email to a contact goes out only through `/send-email`,
only for drafts you have explicitly marked `approved`, and only while you are present.

## Why it is built this way

Three constraints shaped it, and they are worth understanding before you change anything.

**The agent may only say things you can prove.** Claims are restricted to what is written in
`profile/`. The rule is stated in `CLAUDE.md` and enforced mechanically by `MessageQualityGate`,
which rejects a draft containing a claim absent from the candidate's declared facts. This is the
difference between a tool that helps and one that gets you caught out in an interview.

**An unattended run must not be able to embarrass you.** The scheduled job has exactly one send
permission: emailing its own summary to your own address. A `PreToolUse` hook reads the recipient out
of every send call and denies anything else, including an address slipped into bcc. Everything
outbound to a real contact requires you.

**Silence is not success.** A headless agent denied every tool still exits 0. The runner therefore
refuses to report success unless the summary file was actually rewritten by that run.

## Architecture

```
CLAUDE.md                 operating rules: hard limits, writing rules, audience angles
.claude/skills/           one skill per task, invoked as /find-jobs, /daily, and so on
engine/outreach_engine/   decision logic, as a normal installable Python package
profile/                  who you are. The only source of claims about you.
targets/                  what counts as a good role, which companies, what the market wants
pipeline/                 CSV state: jobs, contacts, outreach
drafts/                   generated messages and company briefs, for you to read and paste
scripts/                  scheduling, report rendering, the send guard
```

The split matters. **Skills hold judgement, the engine holds arithmetic.** Anything with a right
answer lives in Python and is unit-tested: scoring a job, ranking a hook, deciding follow-up timing,
classifying a reply, checking a draft. Anything requiring taste stays in the skill prompts, where it
can be argued with in plain language.

| Module | Does |
|---|---|
| `ranking.JobFitRanker` | scores a posting against the candidate, with per-feature explanations |
| `quality_gate.MessageQualityGate` | rejects drafts on length, banned phrases, generic asks, unverified claims, template similarity |
| `planner.DailyPlanner` | orders the day's outreach and enforces per-contact and per-day caps |
| `hooks.HookMiner` | ranks the possible reasons to contact a person, so the opener is specific |
| `replies.classify` | reads a reply and decides what happens next |
| `sequence` | follow-up timing |

`cd engine && pytest` to check it. See [engine/ARCHITECTURE.md](engine/ARCHITECTURE.md) for the
longer version.

## Setup

Prerequisites: Claude Code, Python 3.11+, and a Claude account with the connectors you want
(Gmail, Google Drive, and whichever job boards you use). Check them with `/mcp` inside a session.

```bash
git clone <your fork> job-search-agent
cd job-search-agent
./scripts/setup.sh                      # creates your git-ignored working files from the examples
cd engine && pip install -e . && pytest && cd ..
```

Then, in order:

1. **Fill `profile/resume.md`** with your resume as plain text.
2. **Fill `profile/background.md`.** Be specific and numeric. Every proof point here is something the
   agent may put in a message, so vague entries produce vague outreach.
3. **Paste real messages into `profile/voice-samples.md`.** Skip this and your drafts will sound like
   the tool rather than like you. It is the highest-leverage file in the repo.
4. **Fill `targets/criteria.md`**, especially the work-authorisation block. If you need sponsorship,
   say so precisely; it changes which employers are worth any effort at all.
5. **Fill `targets/companies.md`.** Without it the agent can only search job boards, which skew
   heavily toward staffing firms whose postings have the contact details stripped out.
6. **Edit `CLAUDE.md`** so the name, the email signature and the shared-background hooks are yours.

Then try it interactively:

```
/find-jobs
/research-company <name>
/find-contacts <company>
/draft-outreach <contact id>
```

Read what lands in `drafts/`. If the voice is wrong, add more voice samples and say what is off.

## Scheduling the daily run

`scripts/daily.sh` runs the whole pass headlessly (`scripts/daily.ps1` for Windows Task Scheduler).
On macOS, schedule it with launchd rather than cron: `StartCalendarInterval` runs a missed job when
the machine next wakes, whereas cron skips it entirely. Three things to get right:

- **Use an absolute path to the `claude` binary.** launchd does not inherit your shell `PATH`.
- **Grant the headless session its permissions** in `.claude/settings.json`. A non-interactive run
  cannot answer a permission prompt, so without this every tool call is denied and the run does
  nothing while still exiting 0. That file is git-ignored deliberately: it is machine-specific and it
  authorises real access to your mail.
- **Avoid `RunAtLoad`** unless you want a full run at every login. Catch-up-on-wake comes from
  `StartCalendarInterval` on its own.

Run it by hand a few times before trusting the schedule.

## Safety model

- No LinkedIn automation of any kind. Drafts go to `drafts/` and you paste them.
- No outbound email to a contact without your explicit per-draft approval.
- The unattended run may email only you, enforced by a hook rather than by good intentions.
- No invented facts about you or about a contact. An unverifiable hook stays generic.
- Low daily volume caps.

## Adapting it

The candidate in the examples is fictional. Everything specific to a person lives in `profile/`,
`targets/` and `CLAUDE.md`; the skills and the engine are generic. The engine is plain Python with no
dependency on Claude Code, so it can be tested and reused on its own.

`profile/`, `pipeline/` and `drafts/` are git-ignored, and only the `*.example.*` files are tracked.
That is intentional: it means you cannot accidentally commit your own resume, your contacts, or your
outreach history to a public fork.

## License

MIT. See [LICENSE](LICENSE). Replace the copyright holder with your own name.
