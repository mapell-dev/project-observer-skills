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
2. Its review proposes changes to the project's own files, plus skills
   through export. It first sorts each lesson as mechanical (a tool can
   detect it) or judgement. Mechanical lessons get an automated check (lint
   rule, test, pre-commit hook, CI job), and an existing check that is not
   wired in comes before a new one. Judgement lessons go to a helper or
   fixture, a test, a runbook, then CLAUDE.md or a personal instruction
   file, in that order. The agent edits the working tree on approval;
   Marcin commits through the team's normal process. (The check-first
   order, the extra lesson kinds and the "quote the moment" rule come from
   the `retro` skill in mattpocock-skills.)
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

One plugin, `project-observer`, in a single-plugin marketplace
(`project-observer-skills`). Under a plugin the skills are namespaced:
`project-observer:project-observer` and `project-observer:project-review`.
They stay siblings in one plugin because project-review runs
`../project-observer/scripts/pobs.py`.

```
.claude-plugin/marketplace.json                   marketplace, source ./plugins/project-observer
plugins/project-observer/.claude-plugin/plugin.json
plugins/project-observer/hooks/hooks.json         SessionStart: one line, only where a log exists
plugins/project-observer/skills/project-observer/SKILL.md            session start, set-up, what and how to log
plugins/project-observer/skills/project-observer/references/review.md       review: lessons into project changes
plugins/project-observer/skills/project-observer/references/generalize.md   generalize, leak check, human read, export
plugins/project-observer/skills/project-observer/scripts/pobs.py     all mechanics, stdlib Python, one file
plugins/project-observer/skills/project-observer/scripts/fixture/    fake project log (Quokka Ledger, Bramblecorp, QKL-)
plugins/project-observer/skills/project-review/SKILL.md              diff review; uses ../project-observer/scripts/pobs.py
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

`python3 plugins/project-observer/skills/project-observer/scripts/pobs.py selftest`
builds a temp git repo, runs `init`, loads the fixture, and asserts 58 facts across every
command (ids, leak check, lint, list, counts M1 to M6 and proposals, archive,
empty-denylist refusal). Mutation checks: weakening the term normalization,
the recurrence date rule, the first-result rule, the ticket-prefix boundary
or the `.git/info/exclude` write each turns the selftest red. Both skills
pass task-observer's `validate-skill-bundle.py`.

Application tests (2026-11-23): a fresh agent followed each SKILL.md in a
fake project, with scripted user answers.

- project-observer: set-up, two lessons logged, review, generalization and
  leak check all ran; lint ended at 0 errors. The agent generalized
  details the denylist did not hold ("invoice" became "an export flow").
  Gaps it found, now fixed: a set-up request now skips the "no log, stop"
  branch; category tiebreak (what the mistake was about, not who made
  it); `reference:` defined; status stays `open` until the commit is
  recorded; backup runs after the review record.
- project-review: two findings on the test branch, both citing lessons;
  one logged as a recurrence after the fix (M5). Its own comparison:
  `code-review` would likely flag the fixed sleep, but neither the
  recurrence nor the seed-deletion finding (no CLAUDE.md rule covers it).
  Gaps fixed: `recurs` now always names the lesson's first observation;
  an open run record (minutes not yet given) is a lint warning, not an
  error.

## Decisions for Marcin

1. **Log location.** In the checkout (`.project-observer/`, excluded
   locally) vs outside it (`~/.project-observer/<project>/`). In the checkout
   it is visible next to the code and shared by worktrees; the risk is a
   `git clean -x`, which deletes ignored files. The review backs it up to
   `~/.project-observer-backups/`. Chosen: in the checkout.
2. **Activation at the company.** The plugin's own SessionStart hook tells
   the session the log is active, in any project where `.project-observer/`
   exists, and prints nothing elsewhere. Nothing is written into the
   company repo, not even `.claude/settings.local.json`. Your global `~/.claude/CLAUDE.md` also makes task-observer
   start every session; for company sessions the routing rule above depends
   on the agent following project-observer over task-observer. A one-line
   addition to the global CLAUDE.md would make that explicit: "In a repo
   with an active `.project-observer/` log, write observations there;
   task-observer gets only generalized exports." Added to Marcin's global
   CLAUDE.md on 2026-11-23.
3. **Licence and attribution.** CC BY 4.0 for the whole repo (task-observer
   is CC BY 4.0, and the adaptation must credit it), with "Marcin Szupke
   (mapell.dev)" as author. Feedback goes to the public repo,
   https://github.com/mapell-dev/project-observer-skills. The LICENSE file
   holds a summary, the attribution and the full legal code.
4. **What the reviewer does on a recurrence.** project-review logs a new
   observation only when the matched lesson's fix has landed (that is M5
   data). A diff repeating an open lesson becomes a proposal only.

## Pilot label (accepted 2026-11-23)

Observations made before Marcin's predictions are labelled `pilot` and kept
out of M1 to M6; Marcin accepted this rule on 2026-11-23. Supported but
optional: `pilot: true` on an observation, proposal or review
record leaves it out of every count, and `counts` prints how many it left
out. A recurrence may still point at a pilot lesson. Nothing requires the
field, and the skill sets it only when the user says the trial period is
on.

## Go-live gate

The pilot started on 2026-11-23: Marcin installed the plugin at local scope
in the company project. Every record made before the gate below opens
carries `pilot: true`; the user tells the skill that the trial period is on.
Before the first pilot lesson is exported, the denylist must hold his terms.

The gate governs the counted run. The 8-week clock starts on the day the
predictions are committed to the brief, and from then on no new record
carries `pilot`. The gate opens when all hold:

- Marcin's predictions for M1 to M6 are written in
  `publishing-platform/project-observer/BRIEF.md`, Experiment plan;
- Marcin has reviewed this design;
- the denylist is filled in with his terms after `pobs.py init`.

## Not built

- No matcher from changed files to lessons: project-review picks lessons by
  reading the list (an 8-week log is tens of entries). Add a path field and a
  matcher if the list outgrows one read.
- No automatic minutes: Marcin's own number is the metric.
