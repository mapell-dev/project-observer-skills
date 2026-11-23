# Design: project-observer and project-review

Status: draft for Marcin's review, 2026-11-23. Nothing is installed at the
company project. The go-live gate is below.

## What each skill does

**project-observer** is the project-level counterpart of task-observer. It
reuses task-observer's mechanics: one Markdown file per observation with YAML
frontmatter, the id rule (highest of active, archive and `.id-floor`, plus
one), archive after a one-day grace, and the Issue / Improvement / Principle
body. Four things differ:

1. The log lives with the project, in `<main checkout>/.project-observer/`.
   It is ignored through `.git/info/exclude`, which is local to the clone, so
   no shared file (not even `.gitignore`) changes and nothing reaches a
   commit. Every worktree shares one log, because the path comes from
   `git rev-parse --git-common-dir`.
2. Its review proposes changes to the project's own files (CLAUDE.md, a
   personal instruction file, tests, test helpers and fixtures, runbooks),
   plus skills through export. The agent edits the working tree on approval;
   Marcin commits through the team's normal process.
3. A generalize step writes a detail-free copy of each lesson, then a script
   checks it against a local denylist, then Marcin reads it. Only copies that
   pass both may leave: into the global task-observer log or an article.
4. While the project log is active, every observation from that project goes
   to it first, including ones about skills; task-observer gets the
   generalized copy. This closes a hole: task-observer is active in every
   session and would otherwise write company details into the global log.

**project-review** reads the current diff and checks it against the lessons
in the log. It proposes, never applies, and records each proposal with its
outcome. Its difference from `code-review`, `simplify` and `ponytail-review`:
every proposal must cite a lesson id from the project's own record of past
mistakes. A finding with no lesson behind it belongs to those reviews.

## Files

```
skills/project-observer/SKILL.md            session start, set-up, what and how to log
skills/project-observer/references/review.md       weekly review: lessons into project changes
skills/project-observer/references/generalize.md   generalize, leak check, human read, export
skills/project-observer/scripts/pobs.py     all mechanics, stdlib Python, one file
skills/project-observer/scripts/fixture/    fake project log (Quokka Ledger, Bramblecorp, QKL-)
skills/project-review/SKILL.md              diff review; uses ../project-observer/scripts/pobs.py
```

The log in a project:

```
.project-observer/
  observations/NNNN-slug.md    lessons (project details allowed)
  observations/archive/        resolved lessons, .id-floor
  generalized/NNNN-slug.md     detail-free copy of lesson NNNN
  proposals/NNNN-slug.md       project-review proposals, .id-floor
  reviews/DATE-observer.md     observer review record (minutes)
  reviews/DATE-HHMM-diff.md    project-review run record (minutes)
  denylist.txt                 project terms; seeded by init from repo name,
                               remotes and commit e-mail domains
```

## Metrics to fields

| metric | field(s) | where | set by | printed by `pobs.py counts` as |
|---|---|---|---|---|
| M1 lessons per week by category | `date`, `category` (test-design, fixtures-data, flaky-tests, tooling, agent-behavior, other); entries with `recurs` count apart | observation | agent | weekly table, experiment weeks from `--start` |
| M2 lesson turned into a committed project-file change | `status: actioned`, `resolved`, `resolution_files: [...]`, `resolution_commit` | observation | review; commit confirmed by Marcin | share of distinct lessons; `--verify-commits` checks each commit exists and touches the listed files |
| M3 already held by CLAUDE.md or auto-memory | `already_held: held / not-held / ambiguous` | observation | Marcin only, at week 8 | counts per label plus unlabeled |
| M4 leak check per generalized entry | `leak_check`, `leak_check_first`, `leak_checked` (written by the script); `human_read`, `human_read_first` (Marcin's verdict) | generalized entry | script; Marcin | first-run failures, failing now (re-run live against today's denylist), human verdicts, leaks the script missed |
| M5 recurrence after the fix | `recurs: <id of the lesson's first observation>` | observation | agent | recurrences after the fix landed vs repeats before a fix, decided by comparing dates with the target's `resolved` and `resolution_commit` |
| M6 review minutes | `kind: observer / diff`, `minutes` | review record | Marcin's number | per week and total, observer and diff apart |
| project-review proposals | `lessons: [...]`, `outcome: pending / accepted / declined`, `outcome_date`, `reason` | proposal | agent records Marcin's answer | totals, acceptance share of decided, proposals per lesson |

Design choices behind the fields:

- One `recurs` field serves both dedup and M5: the script tells "repeat
  before the fix" from "recurrence after the fix", so the agent never has to
  judge it.
- `*_first` fields keep the first result. Without them a rewritten leak
  would erase the evidence that the first generalization leaked, and M4
  would always end at zero.
- "Leaks the script missed" means Marcin's first read found a leak that the
  first script run passed. That is the number the article needs to say how
  much the denylist alone is worth.
- The leak check also reads file names, matches terms of 5+ characters with
  case, spaces and punctuation removed (`Acme Pay` catches `acme-pay` and
  `AcmePay`), and flags any URL or e-mail address. An empty denylist makes it
  exit 2 instead of passing everything.
- `pobs.py leakcheck <file>` works on any file, so the article draft gets the
  same check before it leaves the machine.

## Self-checks

`python3 skills/project-observer/scripts/pobs.py selftest` builds a temp git
repo, runs `init`, loads the fixture, and asserts 55 facts across every
command (ids, leak check, lint, list, counts M1 to M6 and proposals, archive,
empty-denylist refusal). Mutation checks: weakening the term normalization,
the recurrence date rule, the first-result rule, the ticket-prefix boundary
or the `.git/info/exclude` write each turns the selftest red. Both skills
pass task-observer's `validate-skill-bundle.py`.

## Decisions for Marcin

1. **Log location.** In the checkout (`.project-observer/`, excluded
   locally) vs outside it (`~/.project-observer/<project>/`). In the checkout
   it is visible next to the code and shared by worktrees; the risk is a
   `git clean -x`, which deletes ignored files. The review backs it up to
   `~/.project-observer-backups/`. Chosen: in the checkout.
2. **Activation at the company.** A SessionStart hook in
   `.claude/settings.local.json` (local, git-ignored) tells the session the
   log is active. Your global `~/.claude/CLAUDE.md` also makes task-observer
   start every session; for company sessions the routing rule above depends
   on the agent following project-observer over task-observer. A one-line
   addition to the global CLAUDE.md would make that explicit: "In a repo
   with an active `.project-observer/` log, write observations there;
   task-observer gets only generalized exports." Not made; your call.
3. **Licence and attribution.** CC BY 4.0 for the whole repo (task-observer
   is CC BY 4.0, and the adaptation must credit it), with "Marcin Szupke
   (mapell.dev)" as author and mapell.dev as the feedback route until a
   public repo exists. The LICENSE file holds a summary and the legal-code
   link, not the full text; add the full text before publishing.
4. **What the reviewer does on a recurrence.** project-review logs a new
   observation only when the matched lesson's fix has landed (that is M5
   data). A diff repeating an open lesson becomes a proposal only.

## Go-live gate

Not to be installed in the company project until all hold:

- Marcin's predictions for M1 to M6 are written in
  `publishing-platform/project-observer/BRIEF.md`, Experiment plan;
- Marcin has reviewed this design;
- the denylist is filled in with his terms after `pobs.py init`.

## Not built

- No matcher from changed files to lessons: project-review picks lessons by
  reading the list (an 8-week log is tens of entries). Add a path field and a
  matcher if the list outgrows one read.
- No automatic minutes: Marcin's own number is the metric.
- No plugin packaging: `cp -R` into `~/.claude/skills/` installs both.
