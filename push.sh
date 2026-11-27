#!/usr/bin/env bash
# Publish the given paths on top of the latest main, retrying if another workflow pushed first.
# It copies this run's results aside, resets to origin/main and puts them back, so it also works
# right after the weekly cleanup rewrites the history.
# Usage: COMMIT_MSG="news update" bash push.sh data img
set -u
git config user.name "news-desk-bot"
git config user.email "news-desk-bot@users.noreply.github.com"
tmp=$(mktemp -d)
for p in "$@"; do [ -e "$p" ] && cp -r --parents "$p" "$tmp"; done
for i in 1 2 3 4 5 6; do
  git fetch -q origin main && git reset -q --hard origin/main || { sleep 5; continue; }
  for p in "$@"; do rm -rf "$p"; [ -e "$tmp/$p" ] && mkdir -p "$(dirname "$p")" && cp -r "$tmp/$p" "$p"; done
  git add -A "$@"
  if git diff --cached --quiet; then echo "Nothing changed."; exit 0; fi
  git commit -q -m "${COMMIT_MSG:-update}"
  if git push -q origin HEAD:main; then echo "Pushed."; exit 0; fi
  echo "Push attempt $i failed, retrying..."; sleep $((i * 7))
done
exit 1
