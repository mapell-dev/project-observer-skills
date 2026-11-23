# project-observer skills

Two Claude Code skills for keeping a project's own record of what went
wrong, and using it.

- **project-observer** logs lessons from one project (a test that checked
  the wrong thing, a fixture trap, an agent misstep) in a log that stays
  with the project, reviews them into changes in the project's own files,
  and writes a generalized copy of each lesson that is safe to take
  elsewhere.
- **project-review** checks a diff against those lessons and proposes
  changes, never applying them, and records whether each proposal was
  accepted.

Both are adapted from task-observer ("One Skill to Rule Them All") by
Eoghan Henn / rebelytics.com, CC BY 4.0.

## Install

Install both; project-review uses project-observer's script.

```bash
cp -R skills/project-observer skills/project-review ~/.claude/skills/
```

Then check the scripts on the bundled fixture:

```bash
python3 ~/.claude/skills/project-observer/scripts/pobs.py selftest
```

The skills do nothing in a project until `pobs.py init` has created its
log; set-up steps are in `skills/project-observer/SKILL.md`.

## Where data lives

| what | where | leaves the machine |
|---|---|---|
| lessons, proposals, review records, denylist | `<project checkout>/.project-observer/`, ignored via `.git/info/exclude` | never |
| generalized lessons | `.project-observer/generalized/` | only after `leakcheck` passes and the user has read it |
| backups | `~/.project-observer-backups/<project>/` | never |

## Requirements

Python 3.9+ (standard library only), git 2.31+.

## Licence

CC BY 4.0, see `LICENSE`.
