# AI Agent Bootstrap Preflight — Operations Guide

> PR-013 governance documentation. This document explains how to run
> `scripts/ai_agent_bootstrap_preflight.py`, the single onboarding command
> for coding agents (and human contributors) before they touch files.
> **It adds no new runtime behavior.** It only prints reminders, verifies
> that governance files exist, optionally renders a reusable prompt, and
> orchestrates the existing `scripts/governance_preflight.py` aggregator
> (PR-012) via `subprocess`. See `docs/operations/governance_preflight.md`
> for the underlying aggregate validator this builds on.

## 1. Purpose

AI Agent Bootstrap Preflight ensures that coding agents begin from
Po_core's original design constraints before touching files. It prevents
agents from skipping SSOT, concept drift rules, trace governance, ADR
governance, and schema governance.

## 2. Why AI agents need bootstrap preflight

A fresh coding-agent session has no memory of this repository's governance
history. Without an explicit ritual, an agent can plausibly:

- start editing before reading `docs/STRICT_CORE_RULES.md` or
  `docs/AI_AGENT_INITIALIZATION_RULES.md`;
- rewrite Po_core's public description into a generic chatbot or
  decision-support tool without noticing it violated
  `docs/CONCEPT_DRIFT_GUARD.md`;
- open a PR without ever running `scripts/governance_preflight.py`.

`scripts/ai_agent_bootstrap_preflight.py` makes the "read this first, then
verify, then run governance preflight" ritual a single reproducible
command instead of something every agent has to be reminded of by hand.

## 3. Required reading ritual

The default command prints, in order: the required-reading file list (from
`docs/governance/ai_agent_bootstrap_rules.json`), a canonical-identity
reminder (three-layer tensor intelligence system; 42 philosophers as
deliberation modules inside Po_core; safety as a floor, not a concept
ceiling), and then verifies that the required governance files, scripts,
CI workflows, and coding-agent prompt templates all exist before running
`scripts/governance_preflight.py`.

## 4. Local commands

```bash
python scripts/ai_agent_bootstrap_preflight.py
python scripts/ai_agent_bootstrap_preflight.py --verify-only
python scripts/ai_agent_bootstrap_preflight.py --print-prompt
python scripts/ai_agent_bootstrap_preflight.py --write-prompt /tmp/po_core_agent_prompt.md
python scripts/ai_agent_bootstrap_preflight.py --json
python scripts/ai_agent_bootstrap_preflight.py --list-required-reading
python scripts/ai_agent_bootstrap_preflight.py --skip-governance-preflight
python scripts/ai_agent_bootstrap_preflight.py --rules docs/governance/ai_agent_bootstrap_rules.json
```

`--skip-governance-preflight` prints a warning and should not be used for
final PR validation unless justified — use it only for a quick sanity
check mid-session.

## 5. Prompt template generation

Two reusable prompt files live under `docs/prompts/`:

- `docs/prompts/CODING_AGENT_BOOTSTRAP_PROMPT.md` — a reusable prompt
  header with required reading, canonical identity, and concept-shrinkage
  warnings for any coding agent working in this repository.
- `docs/prompts/CODING_AGENT_TASK_PROMPT_TEMPLATE.md` — a reusable task
  shell with placeholders (`<PR-ID>`, `<TITLE>`, mission, scope,
  acceptance criteria) for handing a single scoped PR to a coding agent.

`--print-prompt` prints `docs/prompts/CODING_AGENT_BOOTSTRAP_PROMPT.md` to
stdout after verification. `--write-prompt PATH` writes a combined prompt
(the bootstrap prompt file plus the required reading list, canonical
identity reminder, and governance command reminders) to `PATH`. This is
the only flag allowed to write a file outside stdout, and it never writes
unless explicitly requested.

## 6. CI workflow explanation

`.github/workflows/ai-agent-bootstrap.yml` runs on `pull_request` when
governance, docs, schema, example, or script paths change, and can also be
triggered manually via `workflow_dispatch`. It is governance-only: it
installs only `pytest` and `jsonschema`, runs
`--verify-only`, `--print-prompt`, and the default command (which in turn
runs the full `scripts/governance_preflight.py` aggregate), then runs
`tests/test_ai_agent_bootstrap_preflight.py`. It requires no secrets or
network access, publishes no artifacts, and does not mutate the
repository. It does not replace `Governance Preflight` or the individual
`Concept Drift` / `Trace Continuity` / `ADR Index` workflows.

## 7. Exit codes

| Code | Meaning                                                                                     |
|------|-----------------------------------------------------------------------------------------------|
| `0`  | All selected checks passed (or governance preflight was explicitly skipped and nothing was missing). |
| `1`  | A required reading file, governance file, script, workflow, or prompt template is missing.    |
| `2`  | `governance_preflight` failed.                                                                |
| `3`  | CLI/config usage error (e.g. missing or invalid `--rules` file).                              |
| `4`  | `--write-prompt` failed to write its output file.                                             |

If both required files are missing and `governance_preflight` would have
failed, the command returns `1` — bootstrap prerequisites are checked
first, and `governance_preflight` is not run until they pass.

## 8. Options

| Option                         | Behavior                                                                                   |
|----------------------------------|---------------------------------------------------------------------------------------------|
| `--verify-only`                 | Only verify required files/scripts/workflows/templates exist. Do not run `governance_preflight`. |
| `--skip-governance-preflight`   | Skip `governance_preflight` and print a warning. Do not use for final PR validation unless justified. |
| `--print-prompt`                | Print `docs/prompts/CODING_AGENT_BOOTSTRAP_PROMPT.md` to stdout after verification.          |
| `--write-prompt PATH`           | Write a combined bootstrap prompt to `PATH`. The only flag allowed to write a file.           |
| `--json`                        | Print a machine-readable JSON summary instead of human-readable text.                        |
| `--list-required-reading`       | Print required reading files and exit `0`.                                                   |
| `--rules PATH`                  | Use an alternate bootstrap rules JSON config (default: `docs/governance/ai_agent_bootstrap_rules.json`). |

## 9. Common failures

### missing_required_reading
Meaning:
A core governance or architecture file is missing.
Fix:
Restore the missing file or complete the earlier governance PR.

### governance_preflight_failed
Meaning:
Concept drift, trace continuity, ADR, or schema validation failed.
Fix:
Run `python scripts/governance_preflight.py` directly and fix the failing
check.

### prompt_template_missing
Meaning:
The reusable coding-agent prompt template is missing.
Fix:
Restore `docs/prompts/CODING_AGENT_BOOTSTRAP_PROMPT.md`.

## 10. What this does not test

This preflight does not test:

- runtime correctness
- performance
- LLM behavior
- philosopher deliberation
- Viewer UI
- REST API
- actual content rewriting
- production release readiness

## 11. Future extensions

- Optional future: AI-agent preflight log attached to PRs.
- Optional future: generated task prompt includes changed-file-specific
  validators.
- Optional future: branch protection for AI Agent Bootstrap.
