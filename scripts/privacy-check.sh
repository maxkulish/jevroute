#!/usr/bin/env bash
# Greps tracked files and the whole history for the local marker list, then runs trufflehog.
# Markers live in .privacy-markers.txt at the repo root (not committed, one fixed string per line).
set -u
root=$(git rev-parse --show-toplevel) || exit 2
markers="$root/.privacy-markers.txt"
[ -s "$markers" ] || { echo "missing or empty $markers"; exit 2; }
rc=0
while IFS= read -r m; do
  [ -n "$m" ] || continue
  if git -c core.quotepath=off grep -I -n -F -e "$m" HEAD -- . >/dev/null 2>&1; then
    echo "tracked tree: $m"; git grep -I -n -F -e "$m" HEAD -- . | cut -c1-160; rc=1
  fi
  if git log --all -p --format=%H -S"$m" -- . | grep -q -F -e "$m"; then
    echo "history: $m"; git log --all --oneline -S"$m" -- . | head -5; rc=1
  fi
done < "$markers"
if command -v trufflehog >/dev/null; then
  out=$(trufflehog filesystem "$root" --exclude-paths <(printf '%s\n' '\.git/' 'listing\.jsonl$' 'code-transcript\.jsonl$') --no-update --json 2>/dev/null | grep -c '"DetectorName"' || true)
  [ "${out:-0}" = "0" ] || { echo "trufflehog: $out findings"; rc=1; }
else
  echo "trufflehog not installed, secrets scan skipped"
fi
[ $rc -eq 0 ] && echo clean
exit $rc
