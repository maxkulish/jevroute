# jevroute - PRD v1

Date: 2026-09-29. Owner: Max. Status: draft for review.

## 1. Problem

Claude Code gives the model a listing of every installed skill at the start of a session, and the model
decides on its own when to load one. With about 150 skills listed, it sometimes misses the one that fits,
especially when several skills overlap (three debugging skills, three code-review skills) or when the prompt
does not use the skill's own words.

TypeSafe's Jev model is a decision-only model: it takes a state and typed questions and returns labels with
probabilities instead of text. It answers in about 300 ms and costs a fraction of a cent per call, so it can
run on every prompt.

## 2. What we learned before this PRD

A community mod, `jev-skill-suggestion`, already used Jev for skill choice. We tested it on 55 labelled
prompts in September 2026. It hid the normal skill listing and replaced it with Jev's pick, and its two-step
gate threw away 8 of the 45 prompts that needed a skill. It also sent raw prompts to TypeSafe. Our verdict was
not to install it.

The same test showed that Jev's ranking itself was strong: its top pick was right on every prompt that needed
a skill. A follow-up probe compared decision pipelines on the 55 prompts plus 50 held-out prompts written by a
separate agent. The best pipeline used one request with a carefully worded "no skill" option, summed
near-duplicate skills into one canonical skill, and only acted at a probability of 0.9 or higher. Against the
real session listing it scored:

| set | right | wrong | needless | missed | request p50 |
|---|---|---|---|---|---|
| dev (55) | 53 | 0 | 0 | 2 | 297 ms |
| held-out (50) | 46 | 0 | 0 | 4 | 298 ms |

All six errors were misses. That result shaped the product: keep Claude's own listing, and let Jev add a hint
only when it is confident. A missed hint then costs nothing, and a wrong hint is the one error to avoid.

## 3. Product

jevroute is a small Rust CLI that runs as a Claude Code `UserPromptSubmit` hook. For each prompt typed in an
allowed project, it asks Jev which skill fits. When one clearly fits, it adds one line of context before
Claude sees the prompt:

```
Skill hint (Jev): /diagnose fits this request. Load it with the Skill tool if it matches; ignore otherwise.
```

When no skill fits, when Jev is unsure, or when anything goes wrong, it adds nothing and Claude behaves as it
does today.

## 4. Users and use

One user (Max), on one Mac, in coding projects under `~/Code`. Sessions are interactive Claude Code sessions,
often several in parallel. Speed matters more than coverage: a slow prompt is noticed on every turn, a missed
hint is not.

## 5. Goals and success metrics

jevroute ships only if all four hold. Each is measured before the next milestone starts.

| # | Goal | Metric | Target |
|---|---|---|---|
| G1 | Hints change Claude's behaviour for the better | correct skill loads, hint vs no hint, same prompts | +10 percentage points or more |
| G1 | ...without extra skill loads | needless skill loads on no-skill prompts | at most +1 in 50 |
| G2 | The binary matches the probe | dev + held-out through `jevroute eval` | 99/105 right, 0 wrong, 0 needless |
| G3 | It holds on prompts it was never tuned on | fresh frozen set of 60 prompts | at least 95% right, 0 wrong, at most 1 needless |
| G4 | It is fast | time from process start to output | p50 <= 400 ms, p95 <= 700 ms |
| G4 | ...and reliable | timeouts + errors, reported separately | under 2% of prompts |

## 6. Non-goals (v1)

- Hiding or rewriting the skill listing, or injecting skill bodies.
- Hints mid-task (tool results, subagents). Only user prompts get a hint.
- Sending conversation context to Jev. A bare follow-up such as "why did that fail" gets no hint.
- A second Jev request, a gate question, or a confidence score in the hint.
- Running outside allowed folders, on other machines, or for other users.
- Retuning thresholds from production logs. Logs carry no labels.

## 7. Requirements

### 7.1 Functional

| ID | Requirement |
|---|---|
| F1 | `jevroute hook` reads the `UserPromptSubmit` JSON from stdin and writes the hint as `additionalContext`, or nothing. It always exits 0. |
| F2 | It runs only when the session cwd matches the allowlist (default `~/Code/**`). A `.jevroute-off` file in the cwd or any parent, or `JEVROUTE=off`, turns it off. |
| F3 | It skips slash commands and empty prompts. |
| F4 | It scrubs the prompt before sending: private keys, known key prefixes, JWTs, `password:`/`token:` values of any length, IBANs with or without spaces, emails, NL phone numbers, 9-digit numbers, long hex and base64 blobs, home paths. |
| F5 | It takes the skill list from the session transcript's `skill_listing` entries, read incrementally from a stored offset. On a session's first prompt it falls back to the last listing seen for the same project. With neither, it skips. |
| F6 | It sends one Jev `choice` request: the scrubbed prompt, every eligible skill (name + listing description), and a "no skill" option with fixed wording. |
| F7 | It applies the config: excluded skills are removed before the request; near-duplicate skills stay separate in the request and their probabilities are summed into the group's canonical skill after the answer. |
| F8 | It emits a hint only if the top option is a skill and its summed probability is at least the threshold (default 0.9). The hint never shows the score. |
| F9 | It appends one line per prompt to a local log: time, outcome class, stage timings, top 3 names with scores. Never the prompt text or a hash of it. |
| F10 | `jevroute key` copies the TypeSafe API key from 1Password into the macOS Keychain once. The hook reads only the Keychain. |
| F11 | `jevroute eval <set.jsonl> --transcript <path>` runs a labelled prompt set through the same code path and prints right / wrong / needless / missed and latency. |
| F12 | `jevroute doctor` checks config, key, network, and shows the skill list the next prompt would use. |

### 7.2 Non-functional

| ID | Requirement |
|---|---|
| N1 | Hard deadline of 700 ms from process start, on a monotonic clock. The HTTP call gets the remaining budget. On deadline, no output. |
| N2 | Fail-open: a missing key, locked Keychain, network error, bad answer or bad cache file never blocks or changes the prompt. |
| N3 | Parallel sessions are safe: every cache write goes to a temp file and is renamed into place. |
| N4 | Config is validated at load: a skill in two groups, an excluded group target, or a threshold outside (0, 1] is an error, and the hook then skips with an `error:config` outcome. |
| N5 | Rust, static binary, no async runtime. Blocking HTTP with rustls, in-process Keychain access. Startup well under 10 ms. |
| N6 | Standalone repo and release, independent of `lok`. |

## 8. Privacy

- The allowlist is the privacy boundary. Scrubbing is a second layer that catches secrets and identifiers; it
  cannot catch free text such as addresses or case details, and the known failures are kept as tests.
- Folders with personal or case material are never on the allowlist.
- What leaves the machine per prompt: the scrubbed prompt and the names and listing descriptions of the
  eligible skills. Nothing else from the session.
- The API key lives in the Keychain and is never written to a file or a log.

## 9. Configuration

`~/.config/jevroute/config.json`, starting from the frozen probe config:

```json
{
  "model": "jev-latest",
  "threshold": 0.9,
  "deadline_ms": 700,
  "allow": ["~/Code/**"],
  "instructions": "Which of these skills, if any, is the right one to load to help with the user's latest request?",
  "none": "No skill applies: a quick question or fact (even about a tool that has a skill), a small code edit, running a command, or a short reaction or follow-up to the previous reply.",
  "exclude": ["codex:codex-cli-runtime", "codex:codex-result-handling", "codex:gpt-5-4-prompting", "superpowers:using-superpowers", "home:templates:*"],
  "groups": {
    "diagnose": ["superpowers:systematic-debugging", "mattpocock-skills:diagnosing-bugs"],
    "superpowers:brainstorming": ["mattpocock-skills:grilling", "mattpocock-skills:grill-me"],
    "superpowers:requesting-code-review": ["code-review", "mattpocock-skills:code-review"],
    "superpowers:test-driven-development": ["mattpocock-skills:tdd"],
    "triage": ["mattpocock-skills:triage"],
    "to-tasks": ["mattpocock-skills:to-tickets"],
    "handoff": ["mattpocock-skills:handoff"],
    "anthropic-skills:skill-creator": ["skill-creator:skill-creator"]
  }
}
```

A group whose canonical skill is missing from the session's listing is ignored for that prompt, and its
members count on their own.

## 10. Milestones

| | Scope | Exit |
|---|---|---|
| M0 | Behaviour test: the 105 labelled prompts through `claude -p` in a scratch `~/Code` project, with and without a throwaway hook. 10 prompts run to completion and are judged blind. | G1 met, or the project stops. No product code before this exit |
| M1 | Rust binary with F1-F12 and unit tests per module | `jevroute eval` runs |
| M2 | Replay, fresh acceptance set, latency, failure tests (cold cache, locked Keychain, no network, 8 parallel calls, 50 ms deadline) | G2, G3, G4 met |
| M3 | Installed as a user-level hook for one week | keep or remove, based on outcome logs and use |

## 11. Risks

| Risk | Mitigation |
|---|---|
| Hints do not change what Claude loads | M0 measures this before any product code |
| The baseline leaves no room: with the full listing, Haiku and Sonnet named the right skill on 55/55 dev prompts | that test measured naming, not loading; M0 measures live loads, and a baseline above 90% correct loads ends the project |
| The first prompt of a session has no listing yet | per-project fallback; M0 checks when the listing is written |
| A new skill gets no hint until its description is good | listing descriptions are the input; misses cost nothing |
| Jev model update shifts scores | `model` is pinned in config; rerun `jevroute eval` after an alias change |
| TypeSafe outage or slow response | 700 ms deadline, fail-open, timeouts logged separately |
| A prompt with personal content in an allowed folder | scrub + `.jevroute-off` per repo; the allowlist stays narrow |

## 12. Open questions

1. The exact stdin field that carries the prompt (`prompt` or `user_prompt`) and whether `additionalContext` or
   plain stdout is the better output channel. To check against the hooks reference at M1.
2. Whether the transcript already holds a `skill_listing` when the first prompt's hook fires. To check at M0.
3. Whether the hook's `timeout` setting needs to be set explicitly (the default for `UserPromptSubmit` is 30 s).
4. Cost ceiling: at about 8k input tokens per prompt the cost is about USD 0.0003 per prompt. Is a monthly
   cap needed?
