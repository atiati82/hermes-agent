#!/usr/bin/env bash
# Thin shim. The dispatcher lives once, at ~/bin/ai-dispatch (atiati82/mac-bin-helpers):
# 2x Codex (quota-aware account choice + failover), 2x Antigravity, 1x Claude.
# Kept so skills and docs that call scripts/dispatch-codex.sh keep working unchanged.
#
# Usage (unchanged): scripts/dispatch-codex.sh "<task description>" [sandbox-mode]
# Force one account (unchanged): CODEX_ACCOUNT=atiworld|andreas
set -euo pipefail
case "${CODEX_ACCOUNT:-}" in
  atiworld) lane=codex-a ;;
  andreas)  lane=codex-b ;;
  "")       lane=codex ;;
  *) echo "error: CODEX_ACCOUNT must be 'andreas' or 'atiworld'" >&2; exit 1 ;;
esac
exec "${AI_DISPATCH:-$HOME/bin/ai-dispatch}" "$lane" "$@"
