---
name: git-autopush-12h
description: Auto-commit and push the OpenClaw workspace git repo on a schedule (every 12 hours) and verify there are no untracked or uncommitted changes left behind. Use when you need hands-off git hygiene for the workspace, periodic pushes, or a quick “what changed since last push?” check.
---

# Git auto-push (12h)

## What this skill does

- Stage **all** changes in the workspace repo
- Commit if there are changes
- Pull (rebase) then push to `origin/main`
- Fail if there are remaining untracked/unstaged changes after the run

## Assumptions

- Workspace is a git repo and `origin` is configured.
- This VPS uses **SSH deploy key** auth for GitHub.
  - Private key (host-local, NOT in git): `/data/.ssh/openclaw-config-deploy-key`
  - SSH config: `/data/.ssh/config` should include `IdentityFile /data/.ssh/openclaw-config-deploy-key`
- **Do not** store PAT tokens in the repo.

## Run the autopush script

Preferred entrypoint:

- `scripts/autopush.sh`

Example (from repo root):

```bash
bash skills/git-autopush-12h/scripts/autopush.sh
```

## Scheduling (Gateway cron)

Use OpenClaw Gateway cron to run this every 12 hours in an isolated cron session.

- Schedule: cron expression `0 */12 * * *` with `America/New_York` (adjust if needed)
- Payload: agent turn that runs the script via `exec`
- Delivery: `none` (quiet) unless you want notifications

**Note (VPS reality):** if `openclaw cron add` fails with `pairing required`, fix Gateway device auth/pairing first (restart the gateway with the intended auth settings, then retry).
