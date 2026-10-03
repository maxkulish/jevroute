---
id: jevroute-l1
kind: constraint
scope: [eval/m0b, docs/findings]
evidence: [eval/runs/m0b-pilot-armA.jsonl, eval/m0b/summarize.py, docs/findings/2026-10-03-baseline-pilot-stop.md, CLO-863]
learned_at_commit: 1e4a3d93815c7c2883d95089e17677775a63c2d8
last_verified_commit: 1e4a3d93815c7c2883d95089e17677775a63c2d8
status: active
supersedes: null
---

# Measure the no-hook baseline before building a routing hint

Claude Code 2.1.288 with claude-sonnet-5-5 at medium effort loaded the right skill on 69 of 75 skill cases with no hook, no hint and no extra context. The project's own stop rule was 68 or more, so the planned UserPromptSubmit router had no measurable room (+10 pp was the gate) and the project stopped before any binary existed.

How to apply: for any add-on that claims to improve Claude Code's skill selection, run the no-hook arm first on the same case set and the same model pin. Write the stop rule down before the run. Only start the hook arm when the baseline leaves the gate reachable.
