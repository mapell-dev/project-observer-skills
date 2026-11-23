---
id: 3
source: 3
title: A month-end test failed on the last day of the month
date: 2025-03-13
leak_check:
leak_check_first:
human_read: leak
human_read_first: leak
exported_to: []
---

**Issue:** A date test in the Wombat service read the real clock.

**Suggested improvement:** Pass a fake clock through the shared test helper.

**Principle:** Time-dependent tests take the clock as input.
