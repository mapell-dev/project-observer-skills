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

Both skills ship as one plugin, `project-observer`, in this repo's
marketplace. Install both skills together: project-review runs
project-observer's script from the sibling directory.

### Claude Code

```
/plugin marketplace add mapell-dev/project-observer-skills
/plugin install project-observer@project-observer-skills
```

The skills then appear as `project-observer:project-observer` and
`project-observer:project-review`. The plugin also adds a SessionStart hook
that prints one line, and only in a project whose log exists.

### GitHub Copilot CLI

Copilot CLI reads the same `.claude-plugin/` manifests:

```bash
copilot plugin marketplace add mapell-dev/project-observer-skills
copilot plugin install project-observer@project-observer-skills
```

The SessionStart hook is written for Claude Code and has not been checked
in Copilot. Activate the skill through your personal instructions instead
(step 3 of "Set up a project").

### Other agents (Agent Skills)

Any agent that reads `SKILL.md` skills can use them without the plugin.
The GitHub CLI (2.90 or later; `gh skill` is in public preview) installs
both skills, scripts included, for the agent you name:

```bash
gh skill install mapell-dev/project-observer-skills --all --agent <agent> --scope user
```

`gh skill install --help` lists the `--agent` values (for example
`github-copilot`, `cursor`, `codex`, `gemini-cli`). Add `--pin <tag or
commit>` to stay on one version, and read what you install first with
`gh skill preview`. Keep `--scope user`: the default scope is `project`,
which writes the skills into the repository you are in (for Copilot,
`.github/skills/`), a change to the project itself. This route installs the
skills only, with no SessionStart hook; activate them through your personal
instructions (step 3 of "Set up a project").

Check the scripts on the bundled fixture from a clone of this repo:

```bash
python3 plugins/project-observer/skills/project-observer/scripts/pobs.py selftest
```

## Set up a project

The skills do nothing in a project until it has a log. Set one up once per
project, from a session started in the project's checkout:

1. Ask the agent to **set up project-observer**. It runs `pobs.py init`,
   which creates `.project-observer/` and adds it to `.git/info/exclude`.
   The output must read `ignored by git: yes; tracked files inside: none`;
   anything else stops the set-up, and nothing is written to a tracked
   file.
2. **Fill in the denylist.** The agent shows the seeded
   `.project-observer/denylist.txt` and asks for the terms it cannot guess:
   client, product, service, team and people names, internal hostnames,
   the ticket prefix (`ABC-`). One term per line. Leave out ordinary words;
   they only make noise. The leak check compares every generalized lesson
   with this list, so do this before you export anything.
3. **Activation.** With the Claude Code plugin, the SessionStart hook
   prints "Project observation log active" in every session started in a
   project whose log exists. That line is one note among the session's
   instructions: an agent can skip it, most likely when your personal
   instructions tell it to start another skill first. Other agents load a
   skill only when they decide its description fits the request, and some
   list extra skills by name alone, so a session can run start to finish
   without it. In every agent, Claude Code included, add this line to your
   personal instructions, which the agent reads in every session:

   > In a repository with a `.project-observer/` directory, load the
   > project-observer skill and run its Session start steps before other
   > work.

   For Claude Code that file is `~/.claude/CLAUDE.md`. For GitHub
   Copilot, in VS Code and in the CLI, it is
   `~/.copilot/copilot-instructions.md` (create it if it is missing; start
   a new chat or session to pick it up; the CLI's `/instructions` lists
   what is loaded). For other agents, use their user-level instructions
   file. Do not put the line in a file inside the repository: that changes
   the project for everyone.
4. **Optional: a trial period.** If the first weeks should not count, tell
   the agent the trial period is on. It then marks new entries
   `pilot: true`, and `counts` leaves them out. Tell it when the trial
   ends.

If you also run task-observer, and especially if your instructions make it
start every session, extend the line so both run and task-observer stays
out of this project's details:

> In a repo with an active `.project-observer/` log, first load the
> project-observer skill and run its Session start steps, then
> task-observer's. Write observations to the project log; task-observer
> gets only generalized exports that passed the leak check.

## Use it

| when | say | what happens |
|---|---|---|
| a test fails for the wrong reason, you correct the agent, a fixture or tool trap bites | nothing, or "log this" | the agent writes a lesson to the log on its own; "log this" makes sure |
| weekly (the agent offers it when the last review is over 7 days old) | "review the project log" | lessons become proposed changes: a check or test first, a CLAUDE.md or runbook line when no check can catch it. A new check must fail once before it counts |
| before a lesson leaves the project | "generalize lesson 0007" or "export to task-observer" | a copy without project details, checked with `leakcheck`, then read by you |
| before you push a branch | "project review" | project-review checks the diff against the lessons and proposes changes; it never edits code |
| at the end of a period | "count the log from YYYY-MM-DD" | `pobs.py counts --start YYYY-MM-DD --weeks 8` prints lessons per week by category, how many became a change, how many your other instructions already held (you label that at the end), recurrences, leaks and review minutes |

The commands behind these steps are listed in
`plugins/project-observer/skills/project-observer/SKILL.md`.

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
