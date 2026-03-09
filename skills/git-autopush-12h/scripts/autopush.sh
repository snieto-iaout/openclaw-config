#!/usr/bin/env bash
set -euo pipefail

# Auto-commit + push the OpenClaw workspace repo.
# Safe-by-default behaviors:
# - Never writes credentials.
# - Fails if repo not clean after attempting to commit/push.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: Not a git repository: $REPO_ROOT" >&2
  exit 2
fi

# Ensure we are on main (best effort; do not force if detached)
current_branch="$(git branch --show-current || true)"
if [[ -n "$current_branch" && "$current_branch" != "main" ]]; then
  echo "WARN: Current branch is '$current_branch' (expected 'main'). Continuing." >&2
fi

# Capture status before
before_status="$(git status --porcelain)"

# Stage everything (including deletions)
git add -A

# Commit only if there is something staged
if git diff --cached --quiet; then
  echo "No staged changes to commit."
else
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  git commit -m "Autopush: $ts"
fi

# Rebase on top of remote main if available
if git remote get-url origin >/dev/null 2>&1; then
  # Don't fail the whole run if remote main doesn't exist yet
  git fetch origin --prune || true
  # Rebase only if origin/main is present
  if git show-ref --verify --quiet refs/remotes/origin/main; then
    git pull --rebase origin main
  fi
  git push origin HEAD:main
else
  echo "WARN: No 'origin' remote configured; skipping push." >&2
fi

# Verify clean
after_status="$(git status --porcelain)"
if [[ -n "$after_status" ]]; then
  echo "ERROR: Repo is not clean after autopush. Remaining status:" >&2
  echo "$after_status" >&2
  exit 3
fi

echo "OK: autopush complete."
