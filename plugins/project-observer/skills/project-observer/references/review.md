# Review: lessons into project changes

The review is where the log pays off or does not: each open lesson gets a
decision, and an approved decision becomes a change in a project file. The
user approves every change; nothing is committed or pushed by the agent.

Run every command from the project checkout, with the skill's base
directory written out as a literal path.

## Steps

1. **Load.** `pobs.py archive`, then `pobs.py lint` (fix errors in records
   before going on), then `pobs.py list`. The queue is every lesson whose
   status is `open` or missing. For each `parked` lesson, check its
   `parked_until` condition; if it is met, set `status: open` and add it to
   the queue.

2. **Close the commit loop.** For each lesson with `resolution_files` and
   no `resolution_commit` (lint warns about them), find the commit:
   `git log --format="%h %ad %s" --date=short -n 5 -- <file>`. Show the
   candidates and ask the user which commit carried the change. On their
   answer set `resolution_commit`, `status: actioned` and
   `resolved: <today>`. A change still not committed stays as it is.

3. **Read and bucket.** Read the body of every queued lesson and sort it
   first:

   - **Mechanical**: the mistake has a fixed shape a tool can detect (a
     banned call such as a fixed sleep, an import shape, a file in the
     wrong folder, a missing `await`). It gets an automated check.
   - **Judgement**: no tool could decide it. It gets one of the other
     destinations.

   Before proposing a new check, read the checks the project already has:
   the lint and test scripts in its build file, the pre-commit config, the
   CI workflow. Extend a check that exists before adding a new one, and
   repair its wiring (a script pointing at the wrong folder, a config that
   skips the test files, a missing folder skipped without an error) in the
   same change. A project where no check runs on commit or in CI is a
   finding of its own: tell the user when you present (step 4), and write
   it into the review record (step 7) for them to take to the team.

   A proposed check counts only once it has gone red. Before presenting
   it, run a copy of it from outside the checkout against the code that
   made the mistake, and show it failing there and passing on the fixed
   code. The working tree stays as it is until approval: work on copies,
   or feed the old file in on stdin, and leave the user's uncommitted
   changes where they are. A runner found elsewhere on this machine
   counts; name it in the proposal. When no runner is available at all
   (missing dependency, no network), say so in the proposal, and say too
   which part of the fix stays unverified (the test the check guards, a
   type-aware parser).

   The proposed change also removes the mistake from the code, so the new
   check passes on the tree it lands in.

   Then give each lesson the first destination that fits:

   | destination | when |
   |---|---|
   | automated check | mechanical: a lint rule, type, test, pre-commit hook or CI job that fails on the mistake |
   | test helper or fixture | a shared helper, factory or fixture that would make the mistake impossible |
   | test | a test that should exist, or a test that checks the wrong thing |
   | runbook or doc | a procedure people and agents follow by hand |
   | CLAUDE.md rule | a judgement rule every session needs while it writes code; CLAUDE.md loads into every session, so a line here costs every session |
   | personal instruction file | a rule for the user only, which the team's shared files should not carry |
   | skill | the lesson is about a skill: export it (`generalize.md`, Export) |
   | decline | already covered, a one-off, or not worth the change; say which |

   A fix that already failed calls for a stronger form (a check instead of
   a rule, a helper instead of a rule): a recurrence after the fix
   (`pobs.py counts` lists them under recurrence), or a mistake made while a rule
   against it already stood. Say which applies.

4. **Present, then ask.** Show the buckets with their counts, then each
   lesson: id, title, destination, the exact change (the lines to add or
   the test to write), and for a check its red and green runs. Ask for approval per lesson or for the whole set. A
   dismissed or unanswered prompt is no approval: stop and ask in plain
   text.

5. **Apply what was approved.** Edit the project file in the working tree.
   Leave committing to the user, who sends it through the team's usual
   review. In the lesson set `resolution_files: [<path>, ...]` and
   `resolution: <what changed and why>`; `status` stays `open` until step 2
   of a later review records the commit. For a decline set `status: declined`,
   `resolved: <today>` and `resolution: <reason>`. For a skill export,
   after the export set `status: actioned`, `resolved: <today>` and
   `resolution: exported to <where>` (no project file, so the change count
   leaves it out, which is correct).

6. **Generalize.** Every lesson without a generalized entry gets one now:
   load `generalize.md` and follow it.

7. **Record the review.** Ask the user how many minutes the review took
   them. Write `reviews/<YYYY-MM-DD>-observer.md`:

```markdown
---
date: <YYYY-MM-DD>
kind: observer
minutes: <the user's number>
---

Reviewed: <ids>. Approved: <id → file>. Declined: <ids>. Exported: <ids>.
```

8. Run `pobs.py lint`.

9. **Back up.** Copy the log to a folder outside the checkout, on this
   machine only:
   `rsync -a <log directory>/ ~/.project-observer-backups/<project folder name>/`

Done when every queued lesson has a decision (approved with the edit made,
declined with a reason, exported, or deferred with the user's reason in the
review record), every lesson has a generalized entry, the review record
holds the user's minutes, lint reports 0 errors, and the backup ran.
