# jevroute - PRD v2

Date: 2026-09-29. Owner: Max. Status: final draft, ready to split into tasks. Design detail:
[docs/design/2026-09-29-jevroute-design.md](../design/2026-09-29-jevroute-design.md).

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
a skill. A follow-up probe compared decision pipelines on the 55 prompts plus 50 prompts written by a
separate agent. The best pipeline used one request with a carefully worded "no skill" option, summed
near-duplicate skills into one canonical skill, and only acted at a probability of 0.9 or higher. Against a
real session listing it scored:

| set | right | wrong | needless | missed | request p50 |
|---|---|---|---|---|---|
| dev (55) | 53 | 0 | 0 | 2 | 297 ms |
| second set (50) | 46 | 0 | 0 | 4 | 298 ms |

All six errors were misses. That result shaped the product: keep Claude's own listing, and let Jev add a hint
only when it is confident. A missed hint then costs nothing, and a wrong hint is the one error to avoid.

Four limits apply to these numbers:

- The threshold and the groups were chosen after seeing both sets. Both sets are therefore development and
  regression sets, not held-out evidence. Only a new, untouched set (G3) shows how the router generalises.
- The listing came from a session in `~/Work/investigations`. Its `mattpocock-skills:*` skills do not exist
  in `~/Code` sessions, so 5 of the 8 groups have no effect where jevroute runs.
- The probe scored a pick as right when it was the canonical skill of an expected skill's group. A swap
  between different workflows (for example `grilling` to `brainstorming`) would have passed. It did not
  change the saved 99/105, but the scoring allowed it.
- The probe sent a hard-coded `jev-latest`, an alias that moves with each release. Today it resolves to
  `jev-1.13.0`, the only released version.

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
often several in parallel, and often in a new git worktree per task. Speed matters more than coverage: a slow
prompt is noticed on every turn, a missed hint is not.

## 5. Goals and success metrics

jevroute ships only if all goals hold. Each is measured at the milestone named, before the next one starts.

### G1 - Hints improve Claude's skill use (M0)

Measured on the 105 development prompts plus 10 short two-turn cases (5 whose second prompt needs a skill, 5
whose second prompt needs none), in three arms: no hook, a generic reminder hook ("check whether a listed
skill fits"), and the Jev hint hook. A two-turn case is scored on its second prompt only. That gives 75
skill cases and 40 no-skill cases. Each case runs 3 times per arm, and every run-level result is kept.

- **Aggregation:** a case counts as correct skill use when at least 2 of its 3 runs are correct. A case's
  unwanted-load count is the median of its 3 runs. Arm totals are sums over cases.

- **Correct skill use:** within the run, Claude calls the Skill tool with a skill from the prompt's expected
  list and the call succeeds, or that skill is already loaded earlier in the same session. A prerequisite
  skill followed by the expected one counts as correct use plus one unwanted load.
- **Unwanted load:** any Skill call on a no-skill prompt, and any Skill call on a skill prompt to a skill
  outside its expected list. Counted over the whole run.

| # | Metric | Target |
|---|---|---|
| G1a | correct skill use on the 75 skill cases, Jev arm vs no hook | +10 percentage points or more |
| G1b | correct skill use on the 75 skill cases, Jev arm vs reminder arm | +5 percentage points or more |
| G1c | unwanted loads on the 40 no-skill cases, Jev arm vs no hook | at most 1 more |
| G1d | unwanted loads on all 115 cases, Jev arm vs reminder arm | not higher |
| G1e | task quality on 10 prompts run to completion, judged blind, Jev arm vs no hook | Jev arm judged worse on at most 1 of 10, and Max reviews every "worse" judgement |

G1e is a smoke test: ten prompts can catch a clear regression but cannot show that quality holds in general.

If G1a holds but G1b does not, the reminder is the better product and the project stops.

### G2 - The binary matches the probe (M1, M2)

| # | Metric | Target |
|---|---|---|
| G2a | per-prompt decisions from recorded Jev responses, binary vs probe policy | identical on all 105 prompts |
| G2b | live `jevroute eval` on the 105 development prompts, pinned model, probe listing | 99/105 right, 0 wrong, 0 needless |

### G3 - It generalises (M2)

A fresh set of 60 prompts, written by a separate agent from a `~/Code` session listing, with labels and class
balance frozen in git before the first run. It includes lookalikes, short follow-ups, prompts from at least two
repos, and prompts that separate the members of each group. Any tuning after its first run turns it into a
development set, and acceptance then needs another untouched set.

| # | Metric | Target |
|---|---|---|
| G3 | fresh set against a `~/Code` listing | at least 95% right, 0 wrong, at most 1 needless |

### G4 - It is fast and reliable (M2, M3)

Latency is measured from outside the process, from launch to process exit, including skip and failure paths.

| # | Metric | Target |
|---|---|---|
| G4a | calls that reach Jev | p50 <= 400 ms, p95 <= 600 ms |
| G4b | every run in the M2 acceptance and failure tests, including failures | at most 750 ms (700 ms deadline + 50 ms exit grace) |
| G4c | skip paths (scope, prompt, short reply, roster) | p95 <= 20 ms |
| G4d | timeouts and errors, reported separately | together under 2% of prompts |

## 6. Non-goals (v1)

- Hiding or rewriting the skill listing, or injecting skill bodies.
- Hints mid-task (tool results, subagents). Only user prompts get a hint.
- Sending conversation context to Jev. A bare follow-up such as "why did that fail" gets no hint.
- A second Jev request, a gate question, or a confidence score in the hint.
- Running outside allowed folders, on other machines, or for other users.
- Retuning thresholds from production logs. Logs carry no labels.

## 7. Requirements

The design document holds the detail behind each requirement: paths, formats and the test list.

### 7.1 Functional

| ID | Requirement | Acceptance |
|---|---|---|
| F1 | `jevroute hook` reads the `UserPromptSubmit` JSON from stdin (`prompt`, `session_id`, `transcript_path`, `cwd`) and writes the hint as `hookSpecificOutput.additionalContext`, or nothing. It always exits 0. | Round-trip test on a recorded hook input; malformed stdin gives no output, exit 0, `error:input`. |
| F2 | It runs only when the session cwd, after resolving symlinks, matches the allowlist (default `~/Code/**`). | A symlink inside `~/Code` that points outside it gives `skip:scope`. |
| F2a | A `.jevroute-off` file in the cwd or any parent, or `JEVROUTE=off`, turns it off. | Both cases give `skip:scope`. |
| F3 | It skips slash commands and empty prompts. | A prompt starting with `/` after trimming, and a blank prompt, give `skip:prompt`. |
| F3a | It skips standalone acknowledgements and choice replies such as "1", "2", "yes", "no", "ok" and "thanks", using a small exact-match list after normalizing case, whitespace and trailing punctuation. It does not skip every prompt under three words. The outcome is logged as `skip:short_reply`. | "Yes." and " 2 " are skipped; "fix it" and "commit this" are not. |
| F4 | It scrubs the prompt before sending: private keys, known key prefixes, JWTs, `password:`/`token:` values of any length, IBANs with or without spaces, emails, NL phone numbers, 9-digit numbers, long hex and base64 blobs, home paths. | Table test passes, including `password: abc123!` and a spaced IBAN, which the probe's scrubber missed. |
| F4a | The same scrub runs on the complete outbound payload, including skill names and descriptions. | A test skill whose description holds an email and a key prefix is sent masked. |
| F5 | It builds the skill list from the session transcript's `skill_listing` entries, read from a stored offset. An entry with `isInitial: true` replaces the list; any other entry adds or updates skills by name. A name missing from a later entry is never treated as removed. | Tests: full listing, delta, repeated name, partial last line, offset resume, truncated or replaced transcript. |
| F5a | When the session has no listing yet, it uses the last listing stored for the project, keyed by the git common directory (so worktrees share it), or by the resolved cwd outside a repo. A stored listing older than 7 days is ignored. With no usable listing, it skips. The age limit bounds staleness; it does not prove that every stored skill exists in the new session. | A new worktree of a known repo gets a hint on its first prompt; an unknown project gives `skip:roster`. |
| F5b | A parallel session replaces the stored project listing only with a listing that has a newer transcript timestamp. The read, compare and replace run under a lock on the project entry, with a bounded wait; if the lock is not free within 20 ms, the write is dropped. The write goes to a temp file and is renamed into place. | 8 parallel writers with different timestamps leave the newest listing, never a partial file, and none waits over 20 ms. |
| F5c | A transcript that contains `skill_listing` entries but parses to zero skills gives `error:roster`, not `skip:roster`. | Fixture with a changed entry shape gives `error:roster`. |
| F6 | It sends one Jev `choice` request: the scrubbed prompt, every eligible skill (name + listing description), and a "no skill" option with fixed wording, using the model named in the config. | The built request equals the frozen probe request for the same prompt and listing. |
| F7 | It applies the config: excluded skills (glob patterns allowed) are removed before the request; near-duplicate skills stay separate in the request and their probabilities are summed into the group's canonical skill after the answer. A group whose canonical skill is missing from the listing is ignored for that prompt. | Tests: glob exclusion, exclusion before groups, group sum, missing canonical. |
| F8 | It emits a hint only if the top option is a skill and its summed probability is at least the threshold (default 0.9). The hint names the canonical skill and never shows the score. | Decision tests at 0.89, 0.90 and a `none` top. |
| F9 | It appends one line per prompt to a local log: time, outcome class, stage timings, top 3 names with scores, roster source (session or project), roster id, model id and config hash. Never the prompt text or a hash of it. A failed log write never changes the output. | Log line schema test; read-only log dir still gives the hint. |
| F10 | `jevroute key` copies the TypeSafe API key from 1Password into the macOS Keychain and grants the current binary access. The hook reads only the Keychain, with the access dialog disabled. | Locked Keychain and a rebuilt, not yet granted binary both give `error:key` and no dialog. |
| F11 | `jevroute eval <set.jsonl> --transcript <path>` runs a labelled prompt set through the same code path, including the F3a short-reply skip, and prints right / wrong / needless / missed, per-prompt decisions and latency. It scores against each prompt's own expected list; a group substitution counts as right only when listed as approved in the set file. With `--responses <file>` it replays recorded Jev responses offline. | Replay of the recorded responses meets G2a. |
| F12 | `jevroute doctor` checks config, key (without a dialog), network, the transcript format, and shows the skill list the next prompt would use and its source. | Each check reports pass or the reason it failed. |

### 7.2 Non-functional

| ID | Requirement |
|---|---|
| N1 | Hard deadline of 700 ms from process start, on a monotonic clock. A watchdog thread started first exits the process with code 0 and no output when the deadline passes, whatever the main thread is doing. If the output write has already started, the watchdog allows it 50 ms and then exits anyway. The output is at most 512 bytes and is written with one `write` call, which is atomic on a pipe, so Claude Code sees the whole hint or nothing. The HTTP call gets the remaining budget. The hook's `timeout` in settings is set to 2 s as a backstop. |
| N2 | Fail-open: a missing key, locked Keychain, network error, bad answer or bad cache file never blocks or changes the prompt. |
| N3 | Bounded work: stdin is capped at 1 MB, new transcript bytes per call at 8 MB, and the Jev response at 1 MB. Over a cap, the hook skips with the matching error outcome. |
| N4 | Config is validated at load: a skill in two groups, an excluded group target, or a threshold outside (0, 1] is an error, and the hook then skips with an `error:config` outcome. `doctor` warns when `model` is an alias. |
| N5 | Rust, single binary with no runtime dependencies beyond macOS system libraries, no async runtime. Blocking HTTP with rustls, in-process Keychain access. |
| N6 | Standalone repo and release, independent of `lok`. |
| N7 | The transcript format is internal to Claude Code and changes between versions. The parser is tested on fixtures from the Claude Code version recorded at M0, and `doctor` checks it against the live format. |

## 8. Privacy

- The allowlist is the privacy boundary, matched on resolved paths. Scrubbing is a second layer that catches
  secrets and identifiers; it cannot catch free text such as addresses or case details, and the known failures
  are kept as tests.
- Folders with personal or case material are never on the allowlist.
- What leaves the machine per prompt: the scrubbed prompt and the scrubbed names and listing descriptions of
  the eligible skills. Nothing else from the session.
- The API key lives in the Keychain and is never written to a file or a log.
- One exception for M3: an opt-in local sample of up to 30 hinted and unhinted turns, with prompt text, in a
  file outside any repo with owner-only permissions. It is judged by hand and deleted when M3 ends.

## 9. Configuration

`~/.config/jevroute/config.json`, starting from the frozen probe config with the model pinned:

```json
{
  "model": "jev-1.13.0",
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

A group sums probability; it does not prove that the canonical skill suits every member's prompts. The
`brainstorming` group joins two different workflows (grilling questions an existing idea, brainstorming
designs a new one), so that substitution is not approved and the labels keep the two apart. In `~/Code`
today only the `diagnose`, `requesting-code-review` and `skill-creator` groups have members present.

## 10. Milestones

| | Scope | Exit |
|---|---|---|
| M0a | Groundwork: record whether the transcript holds a `skill_listing` when the hook fires on the first and second prompt, on the installed Claude Code version; copy the eval data and the probe listing into this repo after a secret scan; map expected skills to names that exist in `~/Code`; list the approved group substitutions; make scoring independent of the config | Findings recorded; eval data and fixtures in the repo |
| M0b | Behaviour test: validate the harness on a small sample, then run three arms through `claude -p` in a scratch `~/Code` project, as in G1, with the Claude model and settings frozen, a fresh session and reset worktree per trial, and arms interleaved | G1 met, or the project stops. No product code before this exit |
| M1 | Rust binary with F1-F12 and unit tests per module; record Jev responses once with the pinned model | `jevroute eval --responses` meets G2a |
| M2 | Live replay, fresh acceptance set, external latency, failure tests (cold cache, locked Keychain, binary not yet granted Keychain access, no network, 8 parallel calls, oversized input, 50 ms deadline, stalled output pipe) | G2b, G3, G4a-c met |
| M3 | Installed as a user-level hook for one week | Keep if G4d holds, `error:roster` never occurs, and at most 1 of the judged hinted turns steered Claude wrong. Otherwise remove |

Rollback at any point: remove the hook entry from `~/.claude/settings.json`, or set `JEVROUTE=off`.

## 11. Dependencies

| Dependency | Status | Risk if it changes |
|---|---|---|
| TypeSafe API `/v1/systemone`, model `jev-1.13.0` | available; key in 1Password | outage handled by fail-open; a new model needs a new eval run |
| Claude Code `UserPromptSubmit` hook contract | documented | low; checked at M1 |
| Claude Code transcript `skill_listing` entries | internal, undocumented | a format change stops hints; caught by F5c, N7 and `doctor` |
| Eval data (`prompts.jsonl`, `heldout.jsonl`, `frozen-v1.json`, probe listing) | in `~/Work/investigations`, copied at M0a | none after the copy |

## 12. Risks

| Risk | Mitigation |
|---|---|
| Hints do not change what Claude loads | M0b measures this before any product code |
| The baseline leaves no room: with the full listing, Haiku and Sonnet named the right skill on 55/55 dev prompts | that test measured naming, not loading; M0b measures live loads, and G1a fails if the baseline leaves less than 10 points |
| A generic reminder does as well as Jev | M0b's reminder arm; G1b stops the project if Jev does not beat it |
| The first prompt of a session has no listing yet | project listing keyed by git common directory; M0a confirms when the listing is written |
| A new skill gets no hint until its description is good | listing descriptions are the input; misses cost nothing |
| A group hints a skill that does not suit the prompt | substitutions approved one by one; G3 includes prompts that separate group members |
| Jev model update shifts scores | versioned model id in config; rerun `jevroute eval` before moving to a new version |
| TypeSafe outage or slow response | 700 ms watchdog, fail-open, timeouts logged separately |
| Claude Code changes the transcript format | F5c reports it as `error:roster`; `doctor` checks the live format |
| A rebuilt binary triggers a Keychain access dialog | dialog disabled; `error:key`; `jevroute key` re-grants access |
| A prompt with personal content in an allowed folder | scrub + `.jevroute-off` per repo; the allowlist stays narrow |

## 13. Open questions

1. Whether the transcript already holds a `skill_listing` when the first prompt's hook fires. Transcripts
   show the listing written in the same batch as the first prompt, so the answer is likely no. M0a confirms
   it on the installed version.

Closed:

- The prompt arrives in the `prompt` field. Plain stdout and `hookSpecificOutput.additionalContext` both add
  context; jevroute uses `additionalContext` (limit 10,000 characters, not shown as a chat message).
- The default hook timeout for `UserPromptSubmit` is 30 s, and hooks block the prompt until they finish.
  jevroute sets `timeout: 2` as a backstop to its own 700 ms deadline.
- Cost: about 8.1k input tokens, USD 0.0003 per prompt; 300 prompts a day is about USD 2.70 a month. No cap.
