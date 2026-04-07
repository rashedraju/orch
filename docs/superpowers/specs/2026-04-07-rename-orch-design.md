# Rename: session-coach → Orch.

**Date:** 2026-04-07

## Context

The session-coach-skill plugin is being rebranded to "Orch." The period is the stylized display form; technical identifiers use plain `orch`. The rename covers all three layers: repository/directory, plugin ID, and all three skill names.

## Naming Map

| Old | New | Context |
|-----|-----|---------|
| `session-coach-skill` | `orch` | repo/dir name, URLs |
| `session-coach` | `orch` | plugin ID, main skill name, paths |
| `coach-planner` | `orch-planner` | skill name, paths |
| `coach-monitor` | `orch-monitor` | skill name, paths |
| `Session Coach` | `Orch.` | display/prose |
| `session-coach plugin` | `Orch. plugin` | prose |
| `<session-coach-context>` | `<orch-context>` | XML tag in hooks |
| `</session-coach-context>` | `</orch-context>` | XML tag in hooks |

## Directory Renames

```
skills/session-coach/          →  skills/orch/
skills/coach-planner/          →  skills/orch-planner/
skills/coach-monitor/          →  skills/orch-monitor/
.claude/skills/session-coach/  →  .claude/skills/orch/
session-coach-skill/           →  orch/   (filesystem, done by user post-merge)
```

## Files Modified

**Plugin metadata:** `.claude-plugin/plugin.json`

**Skill files (frontmatter + body):**
- `skills/orch/SKILL.md`
- `skills/orch-planner/SKILL.md`
- `skills/orch-monitor/SKILL.md`
- `.claude/skills/orch/SKILL.md` (dev copy)

**Hooks:** `hooks/session-start.py`, `hooks/prompt-submit.py`, `hooks/stop-hook.py`, `hooks/pre-compact.py`

**Scripts:** `skills/orch/scripts/init_setup.py`

**Config/CI:** `.gitignore`, `.github/workflows/lint.yml`, `requirements.txt`

**Docs:** `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, `AGENTS.md`

## Notes

- `skills/orch/references/setup.md` and `.claude/skills/orch/references/setup.md` are auto-generated and gitignored — they will be regenerated correctly on the next `init_setup.py` run.
- The working directory rename (`session-coach-skill/` → `orch/`) and GitHub repo rename are done outside git history by the user.

## Verification

```bash
grep -r "session-coach" . --exclude-dir=.git   # should be zero
grep -r "coach-planner" . --exclude-dir=.git   # should be zero
grep -r "coach-monitor" . --exclude-dir=.git   # should be zero
echo '{"cwd": "/tmp", "user_prompt": "i want to add something"}' | python3 hooks/prompt-submit.py
python3 -m py_compile skills/orch/scripts/init_setup.py
```
