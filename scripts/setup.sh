#!/usr/bin/env bash
# Create your live, git-ignored working files from the committed examples.
# Safe to re-run: it never overwrites a file you already have.
set -euo pipefail
cd "$(dirname "$0")/.."

made=0
for src in profile/*.example.md pipeline/*.example.csv; do
  [ -e "$src" ] || continue
  dst="${src/.example/}"
  if [ -e "$dst" ]; then
    echo "  keep    $dst"
  else
    cp "$src" "$dst"
    echo "  create  $dst"
    made=$((made + 1))
  fi
done

echo
echo "Created $made file(s). Next:"
echo "  1. Edit profile/background.md and profile/resume.md with your own details."
echo "  2. Paste 3-5 of your own messages into profile/voice-samples.md."
echo "  3. Fill targets/criteria.md and targets/companies.md."
echo "  4. cd engine && pip install -e . && pytest"
