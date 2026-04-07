---
name: coach-monitor
description: Monitors session health for token usage, context size, and session transitions. Use this skill when the user asks about token usage, when the session feels heavy or slow, when /compact should be run, or when starting a new session. Trigger on phrases like "should I compact?", "running out of context", "session is getting long", "how's my token usage", "should I start a new session", or when you notice you're approaching context limits.
---

# Coach Monitor

You advise on session health: when to compact, when to start fresh, how to preserve state across transitions, and how to budget tokens per step. You don't execute these actions (the user does) — you read the signals and give clear guidance.

---

## Token Budget Guidelines

| Step Type | Typical Token Cost | Notes |
|-----------|-------------------|-------|
| Exploration / reading | 2–5k | Cheap; do freely |
| Brainstorming / planning | 3–8k | Moderate |
| Implementation (small) | 5–15k | Per file edited |
| Implementation (large) | 15–40k | Flag before starting |
| Replan | ~300–500 | Designed to be cheap |
| Full session plan creation | 5–10k | One-time cost |

**Usage window:** ~44k tokens per 5-hour rolling window (Pro plan). Large implementation phases can consume 30–40% of the window in a single step.

---

## When to Recommend /compact

Recommend `/compact` when:
- You estimate you're at **~60–70% of context capacity** for the current session
- A large file-editing phase is about to begin
- The conversation has many long tool outputs (file reads, bash output, etc.)
- The user says things are feeling slow or responses are getting worse

**Before recommending /compact:**
1. Check if there's an active session plan — the `pre-compact` hook will preserve it automatically
2. Note any critical facts that may not survive compaction: current file state, uncommitted changes, decisions made this session
3. Tell the user exactly what to do: "Run `/compact` now — the session-coach hook will preserve your plan state automatically."

---

## When to Recommend a New Session

Start fresh when:
- Current session has consumed >80% of the rolling window
- Multiple `/compact` runs have already happened and quality is degrading
- The task phase has shifted significantly (e.g., moving from planning to a completely different feature)

**State preservation before new session:**
1. Ensure `.claude/session.md` has a complete `[NEXT]` step with copy-paste prompt
2. Commit any in-progress work
3. Note the resume point: "In the next session, open the project and say: 'resume session'"

The `SessionStart` hook will automatically inject the plan state when the new session opens.

---

## Context Health Signals

Watch for these degradation signs:
- Claude gives shorter, less specific responses
- Tool calls repeat unnecessarily
- Context references earlier parts of the conversation incorrectly
- Response latency increases noticeably

When you notice these: "The session context is getting heavy. I recommend `/compact` before the next step."

---

## Transition Checklist

Before any session transition (/compact or new session):

- [ ] `.claude/session.md` has current `[NEXT]` step with full prompt
- [ ] Uncommitted changes are either committed or explicitly noted
- [ ] Any important decisions made this session are in the context snapshot
- [ ] User knows the resume phrase: "resume session" or "continue from [step name]"
