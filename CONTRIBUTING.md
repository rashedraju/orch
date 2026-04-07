# Contributing to Orch.

## Development setup

1. Clone the repo and ensure Python 3.8+ is available:
   ```bash
   git clone https://github.com/rashed/orch.git
   cd orch
   python3 --version  # should be 3.8+
   ```

2. No external packages needed — all scripts use Python standard library only.

3. The `.claude/` directory contains dev tooling config for Claude Code contributors (skill-creator, commit-commands plugins). It's not required to contribute.

---

## Testing hooks manually

Pipe sample JSON via stdin to any hook. Each hook outputs a JSON block to stdout.

```bash
# SessionStart hook
echo '{"cwd": "/tmp/my-project"}' | python3 hooks/session-start.py

# UserPromptSubmit — fuzzy prompt (should inject brainstorm suggestion)
echo '{"cwd": "/tmp", "user_prompt": "i want to add something for notifications"}' \
  | python3 hooks/prompt-submit.py

# UserPromptSubmit — concrete prompt (should pass through)
echo '{"cwd": "/tmp", "user_prompt": "fix the null check in src/auth.ts line 42"}' \
  | python3 hooks/prompt-submit.py

# Stop hook — with active plan
echo '{"cwd": "/tmp", "session_id": "abc123"}' | python3 hooks/stop-hook.py

# PreCompact hook
echo '{"cwd": "/tmp"}' | python3 hooks/pre-compact.py
```

Expected: all hooks exit 0 and output valid JSON without raising exceptions.

---

## Running evals

The `skills/orch/evals.json` file has 10 test cases covering complexity classification, init phase, install phase, and fuzzy/concrete routing. Run them using the [skill-creator](https://github.com/superpowers-ai/skill-creator) eval workflow:

```bash
# Requires the skill-creator plugin to be installed
# In Claude Code:
# /eval skills/orch/evals.json
```

---

## Syntax checking all scripts

```bash
python3 -m py_compile hooks/session-start.py \
  hooks/prompt-submit.py \
  hooks/stop-hook.py \
  hooks/pre-compact.py \
  skills/orch/scripts/init_setup.py \
  skills/orch/scripts/discover_tools.py \
  skills/orch/scripts/install_plugin.py
```

All should exit silently (no output = success).

---

## Editing skills

- The canonical skill source is `skills/` — not `.claude/skills/` (that's a local dev copy).
- When editing `skills/orch/SKILL.md`: keep the complexity gate table and Quick-tier output format in sync.
- When editing `skills/orch-planner/SKILL.md`: the session.md format and step states live here — do not duplicate them in orch.

---

## Submitting a pull request

1. Fork the repo and create a feature branch
2. Make your changes
3. Run the syntax check above
4. Test affected hooks manually (see section above)
5. Open a PR with a clear description of what changed and why
