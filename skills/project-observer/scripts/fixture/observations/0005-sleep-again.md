---
id: 5
title: Fixed sleep returned in the Quokka payments spec
status: open
category: test-design
area: tests/e2e/payments.spec.ts
date: 2025-03-18
session_context: QKL-520
skill: []
recurs: 1
resolved:
resolution:
already_held:
---

**Issue:** Same fixed-sleep pattern, a new spec file, after the CLAUDE.md rule landed.

**Suggested improvement:** Check whether the rule is placed where test work reads it.

**Principle:** A rule that exists but does not fire is a placement problem.
