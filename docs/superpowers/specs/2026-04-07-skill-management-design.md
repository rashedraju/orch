# Skill Management: Dynamic Routing, Gap Detection & Integrated Creation

**Date:** 2026-04-07  
**Status:** Approved  
**Scope:** `hooks/prompt-submit.py`, `skills/orch/SKILL.md`

---

## Problem

Orch's skill routing is static — a hardcoded table in `SKILL.md` that doesn't check whether recommended skills are actually installed. When a preferred skill is missing, the plan silently degrades. Skill creation is disconnected (routes to `skill-creator` with no session tracking). The result: suboptimal plans and no clear path to filling gaps.

## Goal

Orch proactively detects skill gaps before planning begins, routes dynamically to what's actually available, and integrates skill installation/creation as first-class session steps — without blocking the user or making silent changes.

---

## Architecture

Three responsibilities, two files:

```
UserPromptSubmit hook (prompt-submit.py)
  └── detects task type from prompt signals
  └── checks installed/enabled skills against expected skills for that task type
  └── injects [ORCH] gap notice into context if any skill is missing

orch skill (SKILL.md)
  └── reads injected gap notice and surfaces options to user
  └── replaces static routing table with priority-hint table + dynamic lookup against setup.md
  └── graceful fallback when preferred skill unavailable

orch skill — creation path
  └── user picks "create" → Step 1 in session.md = "Create [skill] using skill-creator"
  └── after creation, runs init_setup.py --force to refresh setup.md
```

No new files. Existing scripts (`install_plugin.py`, `init_setup.py`) reused as-is.

---

## Component 1: Hook — Skill Gap Detection (`prompt-submit.py`)

**What changes:** A new check runs after the existing fuzzy-prompt detection.

**Logic:**

1. Parse prompt for task-type signals using keyword matching (same mechanism as fuzzy detection)
2. Look up expected skills for that task type from a static mapping (mirrors orch routing hints)
3. Read `~/.claude/plugins/installed_plugins.json` + `~/.claude/settings.json` to get enabled skills
4. If any expected skill is not enabled → append to injected context:

```
[ORCH] Skill gap detected: task looks like UI work but `ui-ux-pro-max` is not installed.
Options: install from marketplace | proceed without | create new skill
```

5. If no gaps → inject nothing (zero noise on happy path)

**Constraint:** Notice only — never blocks the prompt.

**Task-type → skill mapping (initial set):**

| Task signal keywords | Expected skills |
|---|---|
| ui, component, layout, design, frontend | `ui-ux-pro-max`, `frontend-design` |
| laravel, php, blade, eloquent | `laravel-specialist`, `php-pro` |
| typescript, ts, type error | `ts-check` |
| bug, error, failing, broken | `systematic-debugging` |
| refactor, extract, clean up | `using-git-worktrees` |

---

## Component 2: Dynamic Routing in Orch Skill (`SKILL.md`)

**What changes:** Static routing table replaced with a priority-hint table + runtime lookup.

**Routing logic:**

1. If `[ORCH] Skill gap detected` notice is in context → surface options before routing:

```
⚠️ Skill gap: `ui-ux-pro-max` not installed.
A) Install now: `python scripts/install_plugin.py --plugin ui-ux-pro-max --marketplace claude-plugins-official`
B) Proceed with available fallback: `frontend-design`
C) Create a new skill: adds "Create ui-skill" as Step 1 in session.md
```

2. Read `Available Skills` section from `references/setup.md` to know what's installed
3. Route to preferred skill if available; otherwise route to fallback; otherwise note gap in session.md header and proceed

**Priority-hint table (replaces static table):**

| Situation | Preferred | Fallback |
|---|---|---|
| Session start (fresh) | `smart-explore` | explore manually |
| All planning phases | `writing-plans` | — (required) |
| UI work | `ui-ux-pro-max` + `frontend-design` | `frontend-design` alone |
| Laravel/PHP work | `laravel-specialist` + `php-pro` | `php-pro` alone |
| TypeScript work | `ts-check` | note gap, proceed |
| After implementation | `verification-before-completion` → `requesting-code-review` | — (required) |
| Session end | `timeline-report` → `finishing-a-development-branch` | skip `timeline-report` |
| Token/context health | `orch-monitor` | — (required) |
| Plan management | `orch-planner` | — (required) |
| Needed skill doesn't exist | `skill-creator` | — |

---

## Component 3: Creation Path

**Trigger:** User picks option C from the gap notice.

**Flow:**

1. Orch adds `Step 1: Create [skill-name] using skill-creator` to `session.md`
2. Step 1 prompt includes: invoke `skill-creator`, name the skill, define its trigger conditions and behavior
3. After skill-creator completes → step prompt includes: run `python scripts/init_setup.py --force` to refresh `setup.md`
4. Orch then continues to Step 2 with the new skill available

**Constraint:** Skill creation is always a visible, tracked step — never silent.

---

## Error Handling

- If `setup.md` is missing or unreadable → fall back to static routing table, log warning
- If `installed_plugins.json` is missing → hook skips gap detection silently
- If gap notice is malformed → Orch ignores it and proceeds with static routing
- Required skills (e.g., `writing-plans`, `orch-planner`) have no fallback — if missing, Orch surfaces an error and stops

---

## Verification

1. **Hook gap detection:** Run `echo '{"cwd": "/tmp", "user_prompt": "I need to build a UI component"}' | python3 hooks/prompt-submit.py` — should include `[ORCH] Skill gap detected` in output if `ui-ux-pro-max` is not enabled
2. **No-gap path:** Same test with a prompt like `"fix this bug"` where `systematic-debugging` IS installed — output should have no `[ORCH]` gap notice
3. **Dynamic routing:** In a session where `ui-ux-pro-max` is not installed, give Orch a UI task — it should route to `frontend-design` with a gap note, not silently use the missing skill
4. **Creation path:** Choose option C for a missing skill — verify `session.md` Step 1 contains skill-creator invocation and `init_setup.py --force`
5. **Post-creation refresh:** After skill-creator step completes, verify `setup.md` lists the new skill
