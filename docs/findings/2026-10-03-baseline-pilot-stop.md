# The no-hook baseline meets the stop rule, so the project stops

**Date**: 3 Oct 2026. **Decision**: stop (project owner). **Issue**: CLO-863.

## Question

PRD v3 made the behaviour test (M0b) start with a pilot: run the no-hook arm once on the 75 skill cases
with the settings the full test would use. If Claude already loads the right skill on 68 or more of them,
goal G1a (10 points more right skill use with the hint than without) has no room, and the project stops
before any product code is written.

## Run

| Setting | Value |
|---------|-------|
| Claude Code | 2.1.288 |
| Model, effort | `claude-sonnet-5-5`, medium |
| Turns, tools | max 3, Skill/Read/Glob/Grep, no MCP |
| Cases | 55 probe prompts, 10 held-out, 10 two-turn |
| Harness | `eval/m0b/run.py`, fresh session and reset worktree per case |
| Results | `eval/runs/m0b-pilot-armA.jsonl` (first line holds the frozen settings) |

## Result

| Verdict | Count |
|---------|-------|
| right skill loaded | 69 |
| expected skill absent from the listing (unmappable) | 3 |
| no skill loaded | 3 |
| unwanted load on a skill case | 1 |

69 of 75 against a stop rule of 68 or more. Even with the 3 unmappable cases counted as misses the rule
holds; counted as right the upper bound is 72.

## What it means

Claude Code picks the skill from its own listing on about 92% of prompts that have a matching skill. A
hint that can at best lift that by a few points does not justify a network call on every prompt, the
latency budget, or the scrub rules the design needed. The eval data, the recorded Jev responses and the
first-prompt listing finding stay in the repo as reference; no binary is built.
