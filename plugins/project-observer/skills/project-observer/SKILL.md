---
name: project-observer
description: Use when a session note says a project observation log is active, when work in such a project hits a mistake worth not repeating (a user correction, a flaky or wrong test, a fixture, data or tooling trap, an agent misstep), or when asked to set up, review, generalize, export or count a project's observation log (.project-observer/).
---

# Project observer

A log of **lessons** from one project: what went wrong, why, and what would
prevent it. The log lives with the project and may name its code, data and
people. A review turns lessons into changes in the project's own files
(CLAUDE.md, tests, test helpers, runbooks). A separate **generalize** step
writes a copy of each lesson with no project details, and only that copy
ever leaves the project.

Adapted from task-observer ("One Skill to Rule Them All") by Eoghan Henn /
rebelytics.com, CC BY 4.0: same one-file-per-observation log, id rule,
archive and Issue / Improvement / Principle body. Changes: the log is
project-scoped and local, its review targets project files, and it adds the
generalize step with a leak check. Licence: CC BY 4.0. Feedback: mapell.dev.

## The boundary

- The log sits in `<main checkout>/.project-observer/`, ignored through
  `.git/info/exclude`, so it never reaches a commit and no shared file
  changes. Every worktree of the project uses the same log.
- A lesson leaves the project only as a **generalized** entry that passed
  `leakcheck` and the user's own read (`human_read: ok`). That covers the
  global task-observer log, an article, a chat with another project.
- While this log is active, every observation made in this project is
  written here, including ones about skills. task-observer receives the
  generalized copy through Export (`references/generalize.md`).

## Commands

All mechanics are in `scripts/pobs.py` in this skill's base directory. Run
it from inside the project checkout, with the base directory written out as
a literal path (no shell variables, so permission checks can read the
command):

```bash
python3 <base directory>/scripts/pobs.py list
```

| command | does |
|---|---|
| `root` | prints the log directory for this project |
| `init` | creates the log, ignores it locally, seeds `denylist.txt` |
| `list [observations\|generalized\|proposals]` | one line per record |
| `next-id observations` | prints the next id (`0012`) and raises the floor |
| `lint` | checks every record's frontmatter; exit 1 on errors |
| `leakcheck [FILE ...]` | checks generalized entries, or any given file, against the denylist |
| `archive` | moves observations resolved before today into `observations/archive/` |
| `counts --start YYYY-MM-DD [--weeks 8] [--verify-commits]` | prints the experiment counts |
| `selftest` | runs all of the above on a fixture with fake project terms |

## Session start

1. Run `pobs.py root`. If the printed directory does not exist, this
   project has no log: when the user asked for set-up, go to the next
   section; otherwise stop here and leave the project untouched.
2. Run `pobs.py list` and `pobs.py lint`. Keep the open lessons' titles in
   mind for the session; say nothing about them unless they bear on the
   work.
3. Review trigger: find the newest `reviews/*-observer.md`. If it is older
   than 7 days (or there is none) and open lessons exist, offer the review
   in one line and carry on with the user's task unless they opt in.

Done when you have the list output, lint reports 0 errors, and the review
offer is made or not due.

## Set-up (only when the user asks)

1. Run `pobs.py init` in the project checkout. It must print
   `ignored by git: yes; tracked files inside: none`; anything else stops
   the set-up.
2. Show the user the seeded `denylist.txt` and ask for the terms it cannot
   guess: client, product, service, team and people names, internal
   hostnames, the ticket prefix (`ABC-`). Ordinary words make noise; ask
   the user to drop them.
3. Tell the user activation needs nothing more: the plugin's SessionStart
   hook prints "Project observation log active" in every session started in
   a project whose log exists, and stays silent everywhere else.

## What is a lesson

Log when work in this project shows something a future session should do
differently:

- the user corrects code, a test or the agent's approach;
- a test fails for a reason other than the code under test (timing, data,
  environment, order);
- a fixture, seed or test-data trap;
- a tool, runner, CI or environment surprise;
- the agent misreads a project convention, skips a step, or breaks a rule
  CLAUDE.md already states (log it anyway: the end-of-run label measures
  exactly that);
- the agent searched long for a file or fact, made a costly tool call for
  little return, or needed information it could not reach (a log, a
  service's state). These are environment lessons, usually `tooling`.

Every lesson comes from a moment you can quote: the failing output, the
command, the user's words. Advice with no such moment behind it is not a
lesson.

A typo fixed once with no pattern behind it is task context, not a lesson.

**Category** (one per lesson; the weekly counts group by it):

| category | the lesson is about |
|---|---|
| `test-design` | what a test checks and how: assertions, waits, structure, coverage |
| `fixtures-data` | seed data, fixtures, factories, mocks, test data ownership |
| `flaky-tests` | a test that passes and fails on the same code |
| `tooling` | runner, CI, build, environment, scripts |
| `agent-behavior` | how the agent worked: commands, conventions, skipped steps |
| `other` | none of the above; say why in `area` |

The category names what the mistake was about, not who made it: an agent
adding a fixed sleep to a test is `test-design`. `agent-behavior` is for
mistakes in how the agent worked that would show up in any kind of code.

## How to log

Write the file silently, in the same turn the lesson shows up. Flush any
pending lesson at each of these events, whichever comes first: a test run
turns green after a fix, the user corrects something, a commit is made.

1. **Repeat check.** Look through `pobs.py list` for the same lesson. If it
   is there, the new file still gets written, with `recurs:` set to the id
   of the lesson's first observation (an entry whose own `recurs` is
   empty). The counts tell a repeat before the fix from a recurrence after
   it.
2. `pobs.py next-id observations` gives the id. Run it once per file.
3. Write `observations/<id>-<short-slug>.md` in the log:

```markdown
---
id: 12
title: <short title; project names allowed>
status: open
category: <one value from the table>
area: <file, folder, suite or workflow concerned>
date: <YYYY-MM-DD>
session_context: <what was being worked on>
skill: []
recurs:
parked_until:
resolved:
resolution:
resolution_files: []
resolution_commit:
already_held:
reference:
---

**Issue:** <what happened, with the moment quoted (failing output, command, the user's words), specific enough to understand in two months>

**Suggested improvement:** <the change, and the project file it belongs in>

**Principle:** <the takeaway in one or two sentences>
```

4. Run `pobs.py lint`. Done when it reports 0 errors.

Field rules:

- `skill:` lists skills the lesson concerns (empty for most).
- `reference:` is a path inside the log directory to saved evidence (a
  test output, a log excerpt). Ticket ids go in `session_context`.
- `pilot: true` (optional, also on proposals and review records) marks an
  entry made during a trial period the user named; `counts` leaves it out.
  Add it only when the user has said the trial period is on.
- `resolution_files`, `resolution_commit`, `resolved`, `resolution` are
  filled by the review (`references/review.md`), never at logging time.
- `already_held` belongs to the user: at the end of the run they label
  each lesson `held`, `not-held` or `ambiguous` (did CLAUDE.md or
  auto-memory already hold it?). Leave it empty.
- Status values: `open`, `actioned`, `declined`, `superseded`, `parked`
  (`parked` needs `parked_until:`, one line naming the condition).

## Changing a lesson

Re-read the one file first, then edit only `status`, `parked_until`,
`resolved`, `resolution`, `resolution_files`, `resolution_commit` or
`recurs`. Archive with `pobs.py archive`, which moves files resolved before
today.

The log is outside git, so git cannot restore it. `git clean -x` and
`git clean -X` delete ignored files: keep `.project-observer/` out of their
scope. The review backs the log up.

## Review, generalize, export, count

- Review: when the trigger fires and the user opts in, or the user asks.
  Load `references/review.md` first.
- Generalize or export: before any text from this log leaves the project,
  including an article draft. Load `references/generalize.md` first.
- Counts: `pobs.py counts --start <go-live date> --verify-commits`.
