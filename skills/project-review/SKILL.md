---
name: project-review
description: Use when asked to check a diff, branch or uncommitted changes against a project's own lessons ("project review", "check this against the log") in a project with a project-observer log (.project-observer/), or to record whether earlier project-review proposals were accepted or declined.
---

# Project review

Checks the current diff against the **lessons** in the project's
project-observer log and proposes changes. It never applies them. Each
proposal and its outcome is recorded, so the log shows how often a past
lesson caught something and how often the user agreed.

What it adds to the other reviews: `code-review` looks for correctness bugs
and broken CLAUDE.md rules, `simplify` and `ponytail-review` look for
complexity. None of them reads the project's own record of what went wrong
before, and most lessons in that record are not in CLAUDE.md yet. This
skill reads that record. Every proposal cites the lesson it comes from; a
finding without a lesson belongs to those other reviews.

Requires the `project-observer` skill installed next to this one: the
script is `<this skill's base directory>/../project-observer/scripts/pobs.py`.
Run it from inside the project checkout, written out as a literal path.
Licence: CC BY 4.0. Feedback: mapell.dev.

## Steps

1. **Log present.** Run `pobs.py root`. If that directory does not exist,
   tell the user the project has no lesson log and stop.

2. **Earlier proposals first.** Run `pobs.py list proposals`. For each
   `pending` one from an earlier run, ask the user: accepted or declined,
   and for a decline, why. Record it in the proposal file as in step 9. A
   proposal the user wants to leave open stays `pending`.

3. **Start the run record.** Write `reviews/<YYYY-MM-DD>-<HHMM>-diff.md` in
   the log; its file name without `.md` is the run id.

```markdown
---
date: <YYYY-MM-DD>
kind: diff
minutes:
diff: <what was reviewed, e.g. main...HEAD plus uncommitted changes>
---
```

4. **Read the diff.** Unless the user named one, take the branch against
   its merge base plus uncommitted work: `git diff main...HEAD` and
   `git diff HEAD` (use the project's default branch name).

5. **Pick the lessons.** Run `pobs.py list`. Every lesson except
   `declined` and `superseded` ones is a candidate. Pick those whose area,
   category or title bears on the changed files or the kind of change, and
   read their bodies, including their recurrences.

6. **Check.** For every changed file and every picked lesson: does the
   diff repeat the mistake, or leave out what the lesson's improvement
   calls for? A finding needs evidence: file, line, and the quoted line.

7. **Record each finding** as a proposal. `pobs.py next-id proposals`
   gives the id (once per file). Write `proposals/<id>-<slug>.md`:

```markdown
---
id: <id>
title: <the proposed change, short>
date: <YYYY-MM-DD>
run: <run id from step 3>
lessons: [<lesson id>, ...]
files: [<changed file>, ...]
outcome: pending
outcome_date:
reason:
---

**Saw:** <file:line and the quoted line>

**Proposal (not applied):** <the change>

**Lesson:** <lesson id and title; why it applies here>
```

8. **Recurrence.** When a finding matches a lesson whose fix has landed
   (`status: actioned` with a `resolution_commit`), the mistake came back
   after the fix. Log it through project-observer as a new observation
   with `recurs:` set to the lesson's first observation: the matched
   entry's own id, or its `recurs` value if it is itself a recurrence.
   Name the new observation when you present the proposals.

9. **Present.** Show each proposal: lesson, evidence, proposed change. Ask
   the user to accept or decline each. Set `outcome`, `outcome_date`, and
   for a decline `reason` in the user's words. Applying an accepted
   proposal is a separate request after the review; the record stays as it
   is.

10. **Close the run.** Ask the user how many minutes the review took them
    and write it into `minutes`. Run `pobs.py lint`.

Done when every changed file was checked against every picked lesson, each
finding is a proposal file with an outcome or `pending`, the run record
holds the minutes, and lint reports 0 errors. A run with no findings is a
result too: its record stays.
