---
id: 2
title: Tests mutated the shared Bramblecorp seed set
status: open
category: fixtures-data
area: tests/fixtures/seed.sql
date: 2025-03-05
session_context: QKL-490, ledger balance tests
skill: []
recurs:
resolved:
resolution:
already_held: held
---

**Issue:** A test deleted rows from the shared seed set that three other suites read.

**Suggested improvement:** Test helper that clones the seed per test.

**Principle:** Tests own their data; shared fixtures are read-only.
