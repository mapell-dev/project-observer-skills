---
id: 1
source: 1
title: End-to-end tests slept for a fixed time instead of waiting for the asserted element
date: 2025-03-06
leak_check:
leak_check_first:
human_read: ok
human_read_first: ok
exported_to: []
---

**Issue:** An agent fixed a flaky end-to-end test by adding a fixed two-second sleep.

**Suggested improvement:** A project rule: wait for the element the test asserts on.

**Principle:** Wait on the UI state the test asserts, not on time.
