# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This repository contains the **session-coach** Claude Code skill — a session strategist skill that plans, sequences, and advises on Claude Code task execution. It lives in `.claude/skills/session-coach/`.

## Skill Architecture

The skill has three core files:

- **`.claude/skills/session-coach/SKILL.md`** — the skill definition loaded by the `Skill` tool. Contains the full session coach logic: complexity gate, living plan format, replan trigger, output behaviour, planning rules, and prompt writing guidelines.
- **`.claude/skills/session-coach/evals.json`** — evaluation test cases (7 scenarios) used to verify the skill behaves correctly. Each eval has a `prompt` and `assertions` array.
- **`.claude/skills/session-coach/references/setup.md`** — user-specific setup reference (models, MCPs, plugins, agents, hooks). Loaded by the skill when verifying tool availability.

## Key Design Concepts

**Complexity Gate** — Every invocation must classify the task as Quick / Standard / Complex before any output. Quick tasks (≤2 steps, obvious fix) get a single prompt block only — no `session.md`. Standard/Complex get a living plan.

**Living Plan** (`.claude/session.md`) — Written to the *project root* where the user is working (not this repo). Never pre-generate more than 2 steps ahead. Steps have states: `[DONE]`, `[NEXT]`, `[STUB]`, `[SKIPPED]`. Exactly one `[NEXT]` at all times.

**Replan Trigger** — Replanning fires only when the user explicitly signals completion ("step done", "move to next step", etc.). It advances exactly one step: mark done → append context snapshot → write new `[NEXT]` → update next stub. Cost: ~300–500 tokens by design.

**Phase Detection** — Fuzzy start (vague idea) → Step 1 is always Brainstorm. Concrete start (spec exists) → Step 1 is Explore & Orient.

## Editing the Skill

When modifying `SKILL.md`:
- The complexity gate table and Quick-tier output format must stay in sync — the gate classifies, the format section defines output for each tier.
- `references/setup.md` contains user-specific state (MCP status, active plugins). Update it when the user's setup changes, not when editing skill logic.
- After changes, run the skill against the evals in `evals.json` to verify behaviour hasn't regressed.

## Running Evals

Evals are manual: load each `evals.json` entry's `prompt` into Claude Code with the session-coach skill active, then check each assertion in the `assertions` array. There is no automated test runner.

## Settings

`.claude/settings.json` controls which plugins are enabled for this repo. Currently only `skill-creator` is explicitly enabled.
