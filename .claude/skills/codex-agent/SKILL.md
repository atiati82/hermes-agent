---
name: codex-agent
description: Dispatch a coding task to Codex CLI (OpenAI GPT-5.6-Luna, ChatGPT-authenticated, load-balanced across 2 accounts), scoped to this repo. Usage: /codex-agent <task> [sandbox-mode]
---

# Codex Agent — GPT-5.6-Luna via Codex CLI

## Purpose

A second, independently-reasoning coding agent for this repo — Codex CLI is
a full agentic coding CLI (its own sandboxing, shell execution, multi-step
planning, file editing), authenticated via ChatGPT accounts rather than
per-token API credits. Ported 2026-09-19 from the setup proven in
`~/localhost` and `~/orgs/atiati82/AskBack`.

## Model policy (operator instruction, 2026-09-18/19)

| Model | Role | Notes |
| --- | --- | --- |
| `gpt-5.6-luna` | **Default, everywhere, at `xhigh` reasoning effort.** | Cheapest/fastest GPT-5.6 tier — the standard, token-efficient choice for support/coding work. |
| `gpt-5.6-sol` | On request only — `CODEX_MODEL=gpt-5.6-sol`. | Never a silent default; asking for it explicitly is the authorization. |
| `gpt-5.6-terra` | Escalation, for a task that genuinely needs more than Luna. | `CODEX_MODEL=gpt-5.6-terra`. |

## Two accounts, load-balanced (operator instruction, 2026-09-19)

- `andreas@migotz.de` — `~/.codex-andreas`
- `atiworld@icloud.com` — `~/.codex` (ChatGPT Team)

`scripts/dispatch-codex.sh` randomly picks one per dispatch to spread usage
across both quotas, and automatically retries on the other account if the
first hits a quota/rate-limit/auth error. Force one side with
`CODEX_ACCOUNT=andreas|atiworld`. Manual switch for an interactive `codex`
session: `~/scripts/codex-account.sh <andreas|atiworld> ...`.

## Behavior

When invoked with `/codex-agent <task> [sandbox-mode]`:

1. Run `scripts/dispatch-codex.sh "<task>" [sandbox-mode]` from the repo root.
2. Codex CLI reads this repo's `AGENTS.md` (if present) itself once its
   working directory is set — no hand-rolled context preamble beyond a
   short discipline reminder.
3. Defaults to `workspace-write` sandbox. Pass `read-only` for analysis-only,
   or `danger-full-access` only for something that genuinely needs
   network/CI/infra access.
4. Reports the final message; review any file changes yourself (`git
   status`, `git diff`) the same as with any other dispatched agent.

## Execution

```bash
scripts/dispatch-codex.sh "Fix the null pointer in src/foo.ts"
```

```bash
# read-only: ask a question, don't touch files
scripts/dispatch-codex.sh "Why does this overflow?" read-only
```

- First argument: the task, in plain English.
- Second argument (optional): sandbox mode. Default `workspace-write`.
- `CODEX_REASONING_EFFORT=max scripts/dispatch-codex.sh ...` for a genuinely
  hard problem.

## Notes

- Codex CLI does not auto-commit unless told to — review and commit changes
  yourself, or say so explicitly in the task.
- Billed via each account's own ChatGPT plan, not per-token credits, but
  still a real resource — don't fire it in a loop without noticing.
