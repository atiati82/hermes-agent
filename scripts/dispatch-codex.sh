#!/usr/bin/env bash
# Dispatch a coding task to Codex CLI (OpenAI GPT-5.6, ChatGPT-account
# authenticated), scoped to this repo.
#
# Ported 2026-09-19 from the setup proven in ~/localhost and
# ~/orgs/atiati82/AskBack (see those repos' own scripts/dispatch-codex.sh
# for the fuller, repo-specific version this was simplified from).
#
# Model policy (operator, 2026-09-18/19):
#   gpt-5.6-luna (default, xhigh effort) — standard model for all repos.
#   gpt-5.6-sol  (on request only, via CODEX_MODEL=gpt-5.6-sol) — never a
#                silent default.
#
# Two ChatGPT accounts, load-balanced (operator instruction, 2026-09-19):
#   andreas@migotz.de   -> ~/.codex-andreas
#   atiworld@icloud.com -> ~/.codex (ChatGPT Team)
# Each call randomly picks one to spread usage across both quotas, and
# automatically retries on the other if the first errors with anything
# quota/rate-limit/auth-shaped. Force one side with
# CODEX_ACCOUNT=andreas|atiworld. Manual switch for an interactive session:
# ~/scripts/codex-account.sh <andreas|atiworld> ...
#
# Usage: scripts/dispatch-codex.sh "<task description>" [sandbox-mode]
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$REPO_ROOT" ]; then
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

CODEX_BIN="${CODEX_BIN:-/opt/homebrew/bin/codex}"
MODEL="${CODEX_MODEL:-gpt-5.6-luna}"
DEFAULT_SANDBOX="${CODEX_SANDBOX:-workspace-write}"
REASONING_EFFORT="${CODEX_REASONING_EFFORT:-xhigh}"

ANDREAS_HOME="$HOME/.codex-andreas"
ATIWORLD_HOME="$HOME/.codex"

if [ ! -x "$CODEX_BIN" ]; then
  echo "error: codex binary not found or not executable at $CODEX_BIN" >&2
  echo "       install with: brew install --cask codex" >&2
  exit 1
fi

if [ "$#" -lt 1 ]; then
  echo "usage: $0 \"<task description>\" [sandbox-mode]" >&2
  echo "       sandbox-mode: read-only | workspace-write (default) | danger-full-access" >&2
  exit 1
fi

TASK="$1"
SANDBOX="${2:-$DEFAULT_SANDBOX}"

case "$SANDBOX" in
  read-only|workspace-write|danger-full-access) ;;
  *)
    echo "error: unknown sandbox mode '$SANDBOX'. Valid: read-only workspace-write danger-full-access" >&2
    exit 1
    ;;
esac

case "${CODEX_ACCOUNT:-}" in
  andreas)  FIRST="$ANDREAS_HOME";  SECOND="$ATIWORLD_HOME" ;;
  atiworld) FIRST="$ATIWORLD_HOME"; SECOND="$ANDREAS_HOME" ;;
  "")
    if [ $((RANDOM % 2)) -eq 0 ]; then
      FIRST="$ANDREAS_HOME"; SECOND="$ATIWORLD_HOME"
    else
      FIRST="$ATIWORLD_HOME"; SECOND="$ANDREAS_HOME"
    fi
    ;;
  *)
    echo "error: CODEX_ACCOUNT must be 'andreas' or 'atiworld'" >&2
    exit 1
    ;;
esac

# workspace-write sandbox denies network access by default (git push, npm
# audit, etc. otherwise fail silently with DNS/connection errors) — see
# ~/localhost/scripts/dispatch-codex.sh's own header for the live-verified
# writeup of this exact failure mode.
NETWORK_ARGS=()
if [ "$SANDBOX" = "workspace-write" ]; then
  NETWORK_ARGS=(-c 'sandbox_workspace_write.network_access=true')
fi

DISCIPLINE_DOCS="this repo's own conventions (AGENTS.md/CLAUDE.md/README, if present -- do not search for files that don't exist here)"
[ -f "$REPO_ROOT/AGENTS.md" ] && DISCIPLINE_DOCS="this repo's own AGENTS.md"

TASK_WITH_DISCIPLINE="Repo-scoped task via dispatch-codex.sh — implement the smallest coherent change that satisfies this, per $DISCIPLINE_DOCS. Never edit .env or anything matching a secret pattern. State what you changed and what you validated when done.

TASK:
$TASK"

QUOTA_OR_AUTH_PATTERN='(out of credits|quota|rate.?limit|usage limit|429|insufficient_quota|not authenticated|not logged in|unauthorized|401)'

run_codex() {
  local home="$1" out="$2"
  CODEX_HOME="$home" "$CODEX_BIN" exec \
    -m "$MODEL" \
    -c "model_reasoning_effort=\"$REASONING_EFFORT\"" \
    "${NETWORK_ARGS[@]}" \
    -C "$REPO_ROOT" \
    -s "$SANDBOX" \
    --ephemeral \
    -o "$out" \
    "$TASK_WITH_DISCIPLINE" \
    < /dev/null 2>"$out.err"
}

OUT="$(mktemp)"
trap 'rm -f "$OUT" "$OUT.err"' EXIT

printf 'Dispatching to Codex CLI: model=%s sandbox=%s reasoning_effort=%s repo=%s account_home=%s\n' \
  "$MODEL" "$SANDBOX" "$REASONING_EFFORT" "$REPO_ROOT" "$FIRST" >&2
printf 'Task: %s\n\n' "$TASK" >&2

run_codex "$FIRST" "$OUT"
STATUS=$?
COMBINED="$(cat "$OUT" "$OUT.err" 2>/dev/null)"

if [ "$STATUS" -ne 0 ] && echo "$COMBINED" | grep -qiE "$QUOTA_OR_AUTH_PATTERN"; then
  echo "warning: account at $FIRST looks quota-exhausted or unauthenticated — failing over to $SECOND" >&2
  run_codex "$SECOND" "$OUT"
  STATUS=$?
fi

echo >&2
echo "--- final message ---" >&2
cat "$OUT"
exit "$STATUS"
