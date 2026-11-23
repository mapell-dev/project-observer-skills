---
id: 1
title: Replace the fixed sleep in payments.spec.ts
date: 2025-03-18
run: 2025-03-18-1030-diff
lessons: [1]
files: [tests/e2e/payments.spec.ts]
outcome: accepted
outcome_date: 2025-03-18
reason:
---

**Saw:** waitForTimeout(1500) at line 40

**Proposal (not applied):** Wait for the payment row instead.

**Lesson:** 0001
