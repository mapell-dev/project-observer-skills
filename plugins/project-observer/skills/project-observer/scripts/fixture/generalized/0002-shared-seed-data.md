---
id: 2
source: 2
title: Tests changed a seed data set that other suites share
date: 2025-03-06
leak_check:
leak_check_first:
human_read: pending
exported_to: []
---

**Issue:** A test deleted rows from the quokka-ledger seed set that other suites read. Ask qa@bramblecorp.example first.

**Suggested improvement:** A helper that gives each test its own copy of the seed data.

**Principle:** Tests own their data; shared fixtures are read-only.
