# Coding Agent Task Prompt Template

> Reusable task-prompt shell for handing a single, scoped PR to a coding
> agent. Copy this file, fill in the placeholders (`<...>`), and use the
> result as the task prompt. Governance/docs only — this file does not run
> code and adds no runtime behavior. Rendered alongside
> `docs/prompts/CODING_AGENT_BOOTSTRAP_PROMPT.md` by
> `scripts/ai_agent_bootstrap_preflight.py --write-prompt`. See
> `docs/operations/ai_agent_bootstrap_preflight.md`.

```md
# Coding Agent Task Prompt

You are working in:
`https://github.com/hiroshitanaka-creator/Po_core_-Original-design`

Implement only:
`<PR-ID>: <TITLE>`

## Required Bootstrap

Before making changes, run or manually follow:

```bash
python scripts/ai_agent_bootstrap_preflight.py --verify-only
```

Read the required files printed by the bootstrap command.

## Mission

<Describe exact task>

## Scope

Allowed:

- ...

Not allowed:

- runtime behavior changes unless explicitly listed
- concept shrinkage
- undocumented schema changes
- undocumented trace changes

## Concept Preservation

- Po_core tensor kernel preserved: yes
- Po_self recursive layer preserved: yes
- Viewer feedback layer preserved: yes
- 42 philosophers remain deliberation modules: yes
- Safety used as floor, not concept ceiling: yes
- Unimplemented concepts labeled honestly: yes

## Acceptance Criteria

1. ...
2. ...

## Required Final Report

- Files created
- Files modified
- Tests/checks run
- Whether runtime behavior changed
- STATUS / ROADMAP / CHANGELOG updates
- What was intentionally not implemented
```
