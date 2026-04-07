---
name: coach-planner
description: Manages the living plan file (.claude/session.md) for the session-coach. Use this skill when you need to create, update, advance, or resume a session plan. Trigger when the user says "step done", "move to next step", "what's my next step", "update the plan", "mark this complete", or when replanning is needed after a phase completes. Also use when reading or writing session.md directly.
---

# Coach Planner

You manage the living plan file for an active coaching session. The plan lives at `.claude/session.md` in the user's project root. Your job is to create it, advance it step by step, and keep it accurate — never pre-generate more than 2 steps ahead.

---

## The session.md Format

```markdown
# session: [task name]
status: [in-progress | paused | complete]
phase: [fuzzy | concrete]
started: [date]
last-updated: [date]

## task summary
[2–3 sentences. Updated as understanding grows.]

## pre-flight notes
[Risks, open questions, decisions made. Appended as discovered.]

## context snapshot
[3–5 bullets of key discoveries. Each replan appends here.
This is what makes replanning accurate without re-reading everything.]

## steps

### [DONE] Step 1 — [Name]
prompt used:
> [the prompt that was run]
outcome: [1–2 sentences of what was learned or produced]

### [NEXT] Step 2 — [Name]
mode: [plan mode | auto mode]
model: [Sonnet | Opus | Haiku + reason if non-default]
skills/agents/mcp: [list with 1-line reason each]
prompt:
--------------------------------------
[exact copy-paste prompt]
--------------------------------------
done when: [verification criterion]
token note: [flag if step is heavy]
decision point: [branching logic if any]

### [STUB] Step 3 — [placeholder name]
> Replanned after Step 2 completes. Likely: [1-line guess].

### [STUB] Step 4-N
> Replanned as steps complete.

## skill map
| Stage | Skills / Agents / MCP |
|---|---|
| [stage] | [skills] |
```

---

## Step States

- `[DONE]` — completed; has outcome summary
- `[NEXT]` — the single current actionable step (exactly one at all times)
- `[STUB]` — not yet planned; has a 1-line guess
- `[SKIPPED]` — consciously skipped with reason

**Stub depth rule:** Never plan more than 2 steps ahead. Future steps are always stubs. Scope shifts after every significant step — pre-planning is waste.

---

## Replan Procedure

When the user signals a step is complete ("step done", "that's finished", "move to next step"):

1. Read `.claude/session.md`
2. Mark current `[NEXT]` as `[DONE]` — add 1-line outcome from what the user described
3. Ask if the outcome is unclear: "What did Step N produce? One sentence is enough."
4. Append 2–4 new discovery bullets to the **context snapshot**
5. Write the new `[NEXT]` step in full detail, informed by what was actually learned
6. Update the next `[STUB]` to reflect updated understanding
7. Update `last-updated` date
8. Output the new `[NEXT]` prompt — copy-paste ready

**Cost:** ~300–500 tokens per replan. Keep it cheap by advancing exactly one step.

---

## Token Safety Rules

- Flag **🛑 STOP** when approaching ~70% token usage in a step
- Recommend `/compact` before large file-editing phases (see `coach-monitor` skill)
- Never plan auto-mode execution with less than 40% usage remaining
- Each replan should end with a one-line preview of the next stub

---

## Mode Rules

- Planning, reviewing, reading specs = **plan mode** (shift+tab)
- Execution, file edits, implementation = **auto mode**
- Never recommend auto mode without a reviewed plan first

---

## Model Selection

- Sonnet 4.6: default for all steps
- Opus 4.6: complex architecture or cross-system reasoning only
- Haiku 4.5: quick status checks or simple lookups only

---

## Session End Sequence

Every plan's final step:
1. `timeline-report` skill → session summary
2. `finishing-a-development-branch` skill → cleanup, PR prep
3. Commit via `commit-commands`
4. Mark session.md `status: complete`
