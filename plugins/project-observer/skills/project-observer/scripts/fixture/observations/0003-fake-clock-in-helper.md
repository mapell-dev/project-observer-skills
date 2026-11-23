---
id: 3
title: Flaky month-end test depended on the real clock
status: open
category: flaky-tests
area: tests/helpers/clock.ts
date: 2025-03-11
session_context: QKL-501, month-end close tests in the Wombat service
skill: []
recurs:
resolved:
resolution:
resolution_files: [tests/helpers/clock.ts]
resolution_commit:
already_held: ambiguous
---

**Issue:** Month-end test failed on the last day of the month.

**Suggested improvement:** Fake clock in the shared helper.

**Principle:** Time-dependent tests take the clock as input.
