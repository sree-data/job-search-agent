#!/usr/bin/env bash
# Runs the daily job-search agent pass in headless mode.
# Scheduled by launchd: ~/Library/LaunchAgents/com.example.jobsearch.daily.plist
#   weekdays 07:00. If the Mac is asleep at 07:00, launchd runs it on the next wake
#   (StartCalendarInterval semantics; see man launchd.plist). No pmset needed.
# launchd does not inherit a login shell PATH, so the binary is referenced absolutely.
set -uo pipefail
cd "$(dirname "$0")/.."

CLAUDE="${CLAUDE_BIN:-$HOME/.local/bin/claude}"
SUMMARY="pipeline/daily-summary.md"

if [ ! -x "$CLAUDE" ]; then
  echo "=== $(date) === ERROR: claude binary not found or not executable at $CLAUDE" >&2
  exit 127
fi

echo "=== $(date) ==="

# Marker file: anything written after this instant is newer than the run start.
STAMP="$(mktemp -t jobsearch-daily-stamp)"
trap 'rm -f "$STAMP"' EXIT

"$CLAUDE" -p "/daily" --output-format text
AGENT_RC=$?

# The agent exits 0 even when every tool was denied, so its exit code proves nothing.
# Treat the run as failed unless the summary was actually rewritten by this run.
if [ ! -f "$SUMMARY" ]; then
  echo "=== FAILED $(date) === $SUMMARY was not created (agent exit $AGENT_RC)" >&2
  exit 1
fi
if [ ! "$SUMMARY" -nt "$STAMP" ]; then
  echo "=== FAILED $(date) === $SUMMARY is stale, not refreshed by this run (agent exit $AGENT_RC)" >&2
  exit 1
fi
if [ "$AGENT_RC" -ne 0 ]; then
  echo "=== FAILED $(date) === agent exited $AGENT_RC" >&2
  exit "$AGENT_RC"
fi

echo "=== finished $(date) === $SUMMARY refreshed"
