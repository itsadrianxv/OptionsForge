# AGENTS_FOCUS.md

This is the canonical operating manual for coding agents working in this repository.

It does not replace `AGENTS.md`. `AGENTS.md` remains the repository policy file for commit behavior, refactoring constraints, and other project-wide rules. This file defines how an AGENT should inspect context, choose commands, edit safely, and verify work.

## Purpose And Audience

Use this document when you are:

- a coding agent editing code in this repository
- a developer supervising or reviewing AGENT-driven changes
- a maintainer updating the AGENT workflow, generated navigation assets, or verification flow

The goal is to keep all AGENT-facing guidance aligned around one workflow and one source-of-truth hierarchy.

## Canonical Workflow

The default AGENT workflow is:

From a source checkout, execute commands from the repository root with `python -m src.cli.app ...`.
If the package is installed into the active environment, the equivalent short alias is `option-scaffold ...`.

1. Run `python -m src.cli.app forge` when you need to create or refresh AGENT assets.
2. Inspect `strategy_spec.toml` and `.focus/context.json`.
3. Edit only files inside the current editable surface.
4. Run `python -m src.cli.app validate --json`.
5. Run `python -m src.cli.app focus test --json`.
6. Run `python -m src.cli.app backtest --json` only when strategy behavior needs execution evidence.
7. Run `python -m src.cli.app run --json` only for runtime workflows, not as the default edit-validation loop.

If a task is local and small, the shortest safe loop is:

```powershell
python -m src.cli.app validate --json
python -m src.cli.app focus test --json
```

If the task changes workflow intent, focus scope, or AGENT assets, start with:

```powershell
python -m src.cli.app forge --json
```

## Source Of Truth Hierarchy

Read these assets in this order:

1. `strategy_spec.toml`
   - high-level strategy intent
   - scaffold preset, enabled capabilities, and acceptance expectations
2. `.focus/context.json`
   - the machine-readable current-context contract
   - preferred input for AGENT navigation and automation
3. `.focus/*.md`
   - human-readable navigation companions
   - use when you need explanation or a reading path, not as the primary machine interface
4. `tests/TEST.md`
   - test plan plus the latest acceptance summary
5. `artifacts/validate/latest.json` and `artifacts/backtest/latest.json`
   - latest structured command results

If these sources disagree:

- treat `AGENTS_FOCUS.md` as the canonical human policy
- treat `strategy_spec.toml` as the canonical intent spec
- treat `.focus/context.json` as the canonical current-context contract
- update the generators and regenerate assets instead of hand-maintaining drift

## Editing Boundaries

Always classify paths before editing:

- `editable`
  - default edit surface
  - AGENT should stay here unless there is a concrete reason to expand scope
- `reference`
  - read for context, dependency tracing, and interface understanding
  - avoid editing unless the task truly requires it
- `frozen`
  - do not edit unless the task explicitly targets generator or repository-policy behavior

Default rule:

- consume `.focus/context.json` first
- do not start with ad hoc repo traversal
- do not scan large directories “just in case” before checking the current focus contract

If you must go beyond the editable surface:

1. confirm the change cannot be completed inside the current editable surface
2. expand scope by the smallest possible step
3. explain the boundary expansion in the delivery summary

## Command Protocol

Prefer structured output by default.

### Single-response commands

Use `--json` and consume the standard JSON envelope:

- `python -m src.cli.app forge --json`
- `python -m src.cli.app focus show --json`
- `python -m src.cli.app validate --json`
- `python -m src.cli.app doctor --json`
- `python -m src.cli.app examples --json`

### Long-running commands

Use `--json` and consume NDJSON event streams:

- `python -m src.cli.app run --json`
- `python -m src.cli.app backtest --json`

The AGENT default should be:

- prefer `--json` whenever it is available
- use plain-text output only for human-only workflows or local debugging

## Verification Rules

Use this default verification order:

1. `python -m src.cli.app validate --json`
2. `python -m src.cli.app focus test --json`
3. `python -m src.cli.app backtest --json` only when behavior or parameter effects need execution evidence
4. `python -m src.cli.app run --json` only when the task is about runtime lifecycle, monitoring, or long-lived execution

Interpret the outputs from:

- the command JSON itself
- `tests/TEST.md`
- `artifacts/validate/latest.json`
- `artifacts/backtest/latest.json`

Do not treat a code edit as complete just because the repo builds. Complete the structured verification loop.

## Pack-Aware Editing

Current focus packs define ownership, entrypoints, and tests.

When working on a pack:

- read the pack entry in `.focus/TASK_ROUTER.md`
- follow `Read first` paths from the pack metadata
- use the pack-owned test selectors before wider regression

Do not re-centralize pack logic back into broad top-level entrypoints when the concrete domain service or infrastructure module already owns it.

## Anti-Patterns

Do not:

- bypass `strategy_spec.toml` when changing workflow intent or AGENT-facing assumptions
- hand-edit generated `.focus/*` files unless the task is specifically about the generators
- rely on plain-text CLI output when `--json` exists
- widen scope beyond the editable surface without a concrete reason
- duplicate strategy logic just for backtest or AGENT convenience when the main contract can be reused
- introduce facade/coordinator layers for domain or infrastructure work unless the task explicitly requires them

## Delivery Checklist

Every AGENT delivery should state:

1. which workflow entrypoint was used
   - `forge`, `validate`, `focus test`, `backtest`, or `run`
2. which source-of-truth assets were consulted
   - at minimum `strategy_spec.toml` and `.focus/context.json` when relevant
3. which surface was edited
   - editable only, or why scope expanded
4. which structured verification steps ran
5. whether `tests/TEST.md` or `artifacts/*/latest.json` changed
6. any remaining risks, skipped checks, or follow-up steps

## Maintenance Rule

If you change AGENT workflow wording or runtime navigation semantics, update the generator/source layer and then regenerate:

```powershell
python -m src.cli.app forge
```

Only commit generated AGENT assets after the generator/source changes that produce them are also included.
