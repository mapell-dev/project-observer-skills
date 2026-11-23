# Generalize and export

A generalized entry is the same lesson told so that nobody can tell which
project it came from. It is the only form of a lesson that leaves the
project. Three checks stand between the log and the outside: the writing
recipe below, `pobs.py leakcheck`, and the user's own read.

## Writing a generalized entry

For lesson `<id>` with no file in `generalized/` yet, write
`generalized/<id>-<generic-slug>.md`. The leak check reads the file name
too, so the slug is generic as well.

```markdown
---
id: <same id as the lesson>
source: <same id>
title: <generalized title>
date: <YYYY-MM-DD>
leak_check:
leak_check_first:
human_read: pending
human_read_first:
exported_to: []
---

**Issue:** <generalized>

**Suggested improvement:** <generalized>

**Principle:** <generalized>
```

The recipe:

- Name **roles**, not names: "an internal billing service", "the shared
  seed data set", "an end-to-end test of a checkout flow".
- Keep the **mechanism**: what failed, why it failed, what prevents it.
  That is the part another project can use.
- Public tools keep their names (Playwright, Jest, GitHub Actions); they
  help the reader and identify no one.
- Paths, ticket ids, versions, dates, people, customer data, internal
  hostnames and exact counts stay in the log.
- Read the finished entry as a colleague from the same company would. If
  the combination of details (the domain plus the stack plus a number)
  points at the project, widen the details until it does not.

## Leak check

1. Run `pobs.py leakcheck`. It writes `leak_check`, `leak_checked` and,
   on the first run only, `leak_check_first` into every generalized entry.
   Those fields belong to the script.
2. For each `FAIL`, rewrite the entry around the reported terms and run it
   again until every entry passes. When a hit is an ordinary word the
   denylist should not hold, ask the user to remove the term; the denylist
   is theirs.

Done when `leakcheck` exits 0.

## The user's read

Ask the user to read every entry with `human_read: pending` (list them
with `pobs.py list generalized`). Record their verdict as they give it:
`human_read: ok` or `human_read: leak`, and the same value in
`human_read_first` if that is still empty. For a leak:

1. ask the user which detail leaked, and ask them to add the term to
   `denylist.txt`, so the script catches it next time;
2. rewrite the entry, rerun `leakcheck`, and ask for a second read.

`human_read_first: leak` with `leak_check_first: pass` is a leak the script
missed; the counts report how many there were.

## Export

An entry may leave the project when `leak_check: pass` and
`human_read: ok` (lint fails an export that skipped either).

- **To task-observer:** write a new observation in the global log by
  task-observer's own rules, with the generalized Issue, Improvement and
  Principle as its body and nothing added from the project log. Then set
  `exported_to: [task-observer#<its id>]` here.
- **To an article or any other text:** copy from the generalized entry
  only. Before the text leaves this machine, run
  `pobs.py leakcheck <path to the draft>`, then add `article:<slug>` to
  `exported_to`.

Done when every export target has passed `leakcheck` and each entry's
`exported_to` names where it went.
