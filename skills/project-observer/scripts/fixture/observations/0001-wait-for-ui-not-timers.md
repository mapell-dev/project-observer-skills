---
id: 1
title: Quokka Ledger e2e tests slept 2s instead of waiting for the ledger table
status: actioned
category: test-design
area: tests/e2e/ledger.spec.ts
date: 2025-03-04
session_context: QKL-482, fixing the Bramblecorp invoice export test
skill: []
recurs:
resolved: 2025-03-06
resolution: Rule added to CLAUDE.md under Testing
resolution_files: [CLAUDE.md]
resolution_commit: __SHA__
already_held: not-held
---

**Issue:** Agent added `waitForTimeout(2000)` in the Quokka Ledger invoice export test.

**Suggested improvement:** CLAUDE.md rule: wait for the ledger table row, never a fixed sleep.

**Principle:** Wait on the UI state the test asserts, not on time.
