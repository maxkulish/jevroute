# jevroute - design

Date: 2026-09-29. Status: final draft. Product requirements:
[docs/prd/2026-09-29-jevroute-prd.md](../prd/2026-09-29-jevroute-prd.md). Evidence from before this repo:
`~/Work/investigations/typesafe/experiments/skill-suggestion/` (`2026-09-29-results.md`, `2026-09-29-probe.md`,
`probe.py`, `frozen-v1.json`).

This document holds the detail behind the PRD requirements. Requirement IDs (F1, N1, G1) refer to the PRD.

## Pipeline

```
prompt typed in a session under ~/Code/**
  -> UserPromptSubmit hook: jevroute hook  (stdin: hook JSON)
       0. watchdog  start the 700 ms deadline thread
       1. input     read stdin (cap 1 MB), parse                            else error:input
       2. env       JEVROUTE=off?                                           then skip:scope
       3. config    load and validate (holds the allowlist)                 else error:config
       4. scope     resolved cwd allowlisted? no .jevroute-off?             else skip:scope
       5. prompt    slash command or empty -> skip:prompt; short reply -> skip:short_reply
       6. roster    this session's listing, else the project's stored listing   else skip:roster
       7. key       Keychain read, dialog disabled                          else error:key
       8. scrub     mask the prompt and every skill name and description; keep the first 4,000 characters
       9. policy    drop excluded skills, build one `choice` request with a `none` option; over 28k est. tokens -> error:request
      10. jev       POST /v1/systemone within the remaining deadline        else error:http / timeout
      11. decide    sum group members into their canonical skill; top != none and >= 0.9 -> hint
      12. output    hint as additionalContext; one line to the outcome log (best effort)
  deadline passed at any step -> watchdog exits 0 with no output
```

The allowlist lives in the config, so the config loads before the scope check. Only the `JEVROUTE=off` check
runs earlier, because it needs nothing else. An invalid config therefore gives `error:config` in every folder,
since the hook cannot tell which folders are allowed. Config, scope and prompt checks all run before any
transcript or Keychain work, so skip paths stay under 20 ms (G4c).

## Modules

One binary crate, one module per unit. Each unit is tested on its own.

| Module | Does | Requirements |
|---|---|---|
| `hookio` | Reads the hook JSON from stdin with a size cap; writes the output JSON in one write | F1, N3 |
| `watchdog` | Starts the deadline thread; exits the process with code 0 and no output at the deadline; guards the single output write | N1 |
| `scope` | Resolves the cwd, matches allowlist globs, looks for `.jevroute-off` up to `/`, reads `JEVROUTE` | F2, F2a |
| `prompt` | Slash-command, empty and short-reply checks | F3, F3a |
| `scrub` | Masks secrets and identifiers in any string | F4, F4a |
| `roster` | Parses `skill_listing` entries from a transcript from an offset; merges; keeps the session and project caches | F5, F5a, F5b, F5c |
| `policy` | Loads and validates config; builds the request; decides | F6, F7, F8, N4 |
| `provider` | Resolves the selected provider (flag, env, config, default) to a URL, model id and Keychain item; the `provider` command's checks, menu and save | F13 |
| `jev` | Blocking HTTP client (rustls) with a deadline and a response size cap, against the resolved provider URL | F6, N1, N3 |
| `secret` | Keychain read with the dialog disabled, one item per provider; the `key` command's write and access grant | F10 |
| `outlog` | Appends one JSON line per call; failures are ignored | F9 |
| `eval` | Runs a labelled set through the same code path; scores; replays recorded responses | F11 |
| `doctor` | Runs the checks, names the provider in use and prints the roster the next prompt would use | F12 |

Crates are chosen at M1. Candidates: `serde_json`, `ureq` (blocking, rustls), `security-framework`,
`regex`, `globset`, `sha2`.

## Hook contract

From the hooks reference (code.claude.com/docs/en/hooks):

- Stdin carries `session_id`, `transcript_path`, `cwd`, `permission_mode`, `hook_event_name` and `prompt`.
  Slash commands arrive with their literal `/...` text in `prompt`.
- Output on a hint:
  `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "<hint>"}}`.
  Context is capped at 10,000 characters and is not shown as a chat message.
- All `UserPromptSubmit` hooks must finish before the prompt reaches Claude, so jevroute's latency is added
  to every prompt. The default timeout is 30 s; the settings entry sets `"timeout": 2`.

Settings entry installed at M3:

```json
{"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "~/.local/bin/jevroute hook", "timeout": 2}]}]}}
```

## Short replies

The exact-match list, compared after lowercasing, collapsing whitespace and stripping trailing `.`, `!`
and `?`: digits `1` to `9`, `yes`, `y`, `no`, `n`, `ok`, `okay`, `thanks`, `thank you`, `go`, `continue`,
`sure`. The list is a constant in `prompt` and is covered by a table test. `eval` goes through the same check,
so a labelled skill prompt that matches the list scores as missed.

## Roster

Claude Code writes each `skill_listing` it sends into the session transcript. The entry is internal and not
documented. Observed shape on 2026-09-29:

```json
{"type": "attachment", "timestamp": "...", "attachment": {"type": "skill_listing", "isInitial": true,
 "skillCount": 160, "names": ["agents-sdk", "..."], "content": "- agents-sdk: Build AI agents ...\n- ..."}}
```

- The first entry of a session has `isInitial: true` and the full listing (132 to 160 skills observed).
- Later entries have `isInitial: false` and hold only the skills that were added or changed (1 to 8 observed).
  A name can appear in several of them.
- The first entry is written in the same batch as the first user message, which appears to be after
  `UserPromptSubmit` hooks run. M0a confirms this on the installed version.
- The listing already reflects precedence, `skillOverrides` (`name-only` entries have no description),
  plugins, bundled and nested skills. jevroute never resolves skills from disk.

Merge rule: an `isInitial: true` entry replaces the roster; any other entry adds or updates skills by name.
Descriptions come from `content` lines of the form `- <name>: <description>`; a line without `: ` is a
name-only entry.

### Caches

| Cache | Path | Holds |
|---|---|---|
| Session | `~/.cache/jevroute/sessions/<session_id>.json` | transcript path, device and inode, byte offset, merged roster, timestamp of the newest listing entry |
| Project | `~/.cache/jevroute/projects/<sha256(project key)>.json` | merged roster, source session id, timestamp of the newest listing entry, write time |

- Each call reads only transcript bytes after the offset, up to 8 MB, and never consumes a partial last line.
- If the transcript's inode changed or its size is below the offset, the session cache is dropped and the
  transcript is read from the start.
- Project key: the git common directory when the cwd is inside a repo (read from `.git` without running
  `git`, so worktrees share it), else the resolved cwd.
- A project entry is used only when this session has no listing yet and the entry's listing timestamp is less
  than 7 days old.
- A writer replaces the project entry only if its listing timestamp is newer than the stored one. Atomic
  rename alone cannot enforce this: two writers can both read the old entry, and the older one can rename
  last. So the read, compare and replace run under an exclusive `flock` on `<entry>.lock`, taken with a
  non-blocking try and retried for at most 20 ms. If the lock is still held, the writer drops its update; the
  next prompt writes again. Inside the lock, the write goes to a temp file in the same directory and is
  renamed into place, so readers, which take no lock, never see a partial file.
- The session cache has a single writer: Claude Code runs a session's hooks one prompt at a time.
- A transcript that contains `skill_listing` entries but yields zero skills gives `error:roster`.

## Scrub

Patterns: private key blocks, known key prefixes (`sk-`, `ghp_`, `xox`, `AKIA` and others), JWTs,
`password`/`token`/`secret` followed by `:` or `=` and a value of any length, IBANs with or without spaces,
emails, NL phone numbers, 9-digit numbers, hex runs of 32+ characters, base64 runs of 40+ characters that
contain at least two digits, and `/Users/<name>` paths. The same function runs on the prompt and on every
skill name and description.

Two rules are tighter than the probe's `scrub()`:

- The keyword rule requires the `:` or `=`. The probe made it optional, so "token counting" in the
  `audit-prompt-caching` and `claude-api` descriptions was redacted.
- The blob rule requires two digits. The probe's rule matched slash-joined word lists in `claude-api`
  (`OpenAI/GPT/Gemini/Llama/Mistral/Cohere/Ollama`).

With both changes, scrubbing the probe listing fixture changes nothing, so F4a keeps the request equal to the
probe's. A test pins this: the scrub of the probe listing must be a no-op.

The table test includes the probe's known failures (`password: abc123!`, a spaced IBAN) as cases that must
now be masked, and an address sentence and a medical sentence that pass through unchanged, marked as known
limits.

## Policy and request

The request follows `frozen-v1.json` exactly: the fixed `instructions` text, one option per eligible skill
(name and description), and a final `none` option with the fixed wording. The model id and the URL come from
the selected provider; the body is otherwise identical for every provider.

- `exclude` accepts exact names and `*` globs and runs before the request.
- Group members stay separate options. After the answer, each member's probability is added to its
  canonical skill, and members are dropped from the ranking.
- A group whose canonical skill is not in the roster is ignored for that prompt; its members rank alone.
- Hint only if the top entry is a skill with a summed probability >= `threshold`. The hint names the
  canonical skill.
- The prompt in the request is the first 4,000 characters of the scrubbed prompt, cut at a character
  boundary, with no marker (F6a). The cut is a size and privacy bound. Measured on 2 Oct: 4,300 characters of
  neutral log lines added to each of the 105 prompts cost 2 hints (paste after the prompt) or 3 (paste
  before) and produced no wrong hint, so the head of the prompt is enough and the order barely matters.
- The request size is estimated as serialized bytes divided by 4. Above 28,000 the hook gives
  `error:request` without calling Jev (N3). Today's listing is 8.1k to 9.4k tokens, so the cap trips only
  when the listing roughly triples.

## Deadline

- The watchdog thread starts first and sleeps until `start + deadline_ms` on a monotonic clock.
- One atomic state value, `pending`, `writing` or `expired`, decides who owns the output:
  - The main thread moves `pending` to `writing` with a compare-and-swap, writes, then exits 0.
  - At the deadline the watchdog tries `pending` to `expired`. If that succeeds, it exits 0 at once, and the
    main thread can no longer start a write.
  - If the state is already `writing`, the watchdog waits a 50 ms grace period and then exits 0 whether the
    write has finished or not.
- A stalled write therefore cannot extend the process past `deadline + 50 ms`. It also cannot produce a
  partial hint, for three reasons:
  - The output is capped at 512 bytes, which is `PIPE_BUF` on macOS. The hint JSON is about 200 bytes, and the
    skill name is capped to keep it under the limit.
  - It goes out in a single `write(2)` call. POSIX makes a pipe write of at most `PIPE_BUF` bytes atomic, so a
    blocked write transfers nothing.
  - `SIGPIPE` is ignored, so a closed reader gives an error instead of killing the process mid-write.
- Failure test for the stall: the harness creates a pipe, fills it until a non-blocking write fails, passes
  the full pipe as the child's stdout, and never reads. The child must exit 0 within 750 ms of launch, and
  the pipe must hold no bytes from the child.
- The HTTP client gets the remaining budget as its total timeout.
- Keychain access uses the no-dialog flag, so it cannot block on a prompt. A slow Keychain read is still
  bounded by the watchdog.
- The outcome log is written before the output only if time allows; logging never delays or cancels a hint.
- A watchdog exit bypasses the main thread's logger, so the watchdog writes its own `timeout` line before it
  exits: one `write(2)` on a log file opened with `O_APPEND` at startup, under 512 bytes. Otherwise the
  timeout rate (G4d) would miss the failures it measures. The M2 external harness checks that every
  launched call has exactly one log line.

## Outcome classes

| Case | Behaviour | Outcome |
|---|---|---|
| Malformed or oversized stdin | no output | `error:input` |
| Not allowlisted or opted out | no output | `skip:scope` |
| Slash command or empty prompt | no output | `skip:prompt` |
| Short reply | no output | `skip:short_reply` |
| Invalid config, or a provider id (config or `JEVROUTE_PROVIDER`) with no entry | no output | `error:config` |
| No usable listing (session or project) | no output | `skip:roster` |
| Listing entries present but none parsed, or transcript read over the cap | no output | `error:roster` |
| Keychain locked, key missing, or access not granted | no output | `error:key` |
| Built request over the 28k-token estimate | no output | `error:request` |
| Network error, non-2xx, or response over the cap | no output | `error:http` |
| Deadline reached | no output | `timeout` |
| Malformed answer | no output | `error:answer` |
| Top is `none` | no output | `none` |
| Top below the threshold | no output | `below-cut` |
| Hint | hint | `hint` |

## Outcome log

`~/.cache/jevroute/outcomes.jsonl`, rotated at 10 MB (one old file kept). One line per call:

```json
{"ts": "...", "outcome": "hint", "ms": {"total": 312, "roster": 3, "key": 4, "http": 298},
 "top": [["diagnose", 0.96], ["none", 0.03], ["code-review", 0.01]], "pick": "diagnose",
 "roster_source": "session", "roster_id": "<sha256 of sorted names, 12 chars>",
 "provider": "typesafe", "model": "jev-1.13.0", "config": "<sha256 of config, 12 chars>"}
```

No prompt text and no hash of it.

## Providers

Modelled on `gcm provider` and `gcm status`, cut down to one model behind several routes.

- Config shape (PRD 9): `provider` selects an entry of `providers`; an entry has `url`, `model` and `key`
  (a 1Password reference for `jevroute key`). Built-in defaults exist for `typesafe` and `openrouter`, so a
  config without `providers` still works; a config entry overrides the built-in one field by field.
- Resolution order: `--provider` (accepted by `eval` and `doctor` only), `JEVROUTE_PROVIDER`, config
  `provider`, then `typesafe`. The resolved id, URL and model are fixed before the watchdog's first check and
  logged with the outcome. An id with no entry is `error:config`, so the hook stays silent rather than
  falling back to another route without being told.
- `jevroute provider`: for each entry, read the Keychain item (dialog disabled), then one live `choice`
  request with a two-option fixture state and the entry's model, timed; report `ready <ms>`, `missing key`
  or `failing <reason>`. Show the menu with the current selection marked, save the pick with the same
  atomic write the caches use, and print what `doctor` would print for it. `--set <id>` skips the menu and
  the live check. `--json` prints the table for scripts.
- Keychain items are named `jevroute/<provider id>`; `jevroute key` acts on the selected provider unless
  `--provider` says otherwise.
- Adding a provider later is one built-in entry plus a fixture response; nothing in `policy`, `scrub` or
  `roster` changes. A keyless local provider (Ollama) would set `key` to null and skip the Keychain step; the
  26-option and 8k-token limits measured on 1 Oct would need their own `error:request` rule, which is why it is
  not in v1.
- OpenRouter specifics: the global hostname only (`eu.`/`us.` need a paid plan), the workspace guardrail
  must keep the global data region, and a 200 can carry an `error` object (seen on the router endpoint on
  2 Oct), so the client treats a body without `answers` as `error:answer`.

## Keychain

- `jevroute key` reads the selected provider's key from 1Password with `op read`, stores it as a generic
  password item named `jevroute/<provider id>`, and adds the current binary to the item's access list.
- The hook reads the item with the dialog disabled. A rebuilt binary has a new code signature and is not on
  the list, so the read fails with `error:key` until `jevroute key` runs again. `doctor` reports this.
- M1 measures the read latency. If it is over 50 ms, that is recorded as a finding for M2.

## Evaluation

### Prompt set format

```json
{"id": "p01", "kind": "clear", "prompt": "...", "expected": ["diagnose"], "setup": ["..."]}
```

- `expected` is written by the labeller and is never widened by the config's groups.
- `setup` is optional: earlier user turns for a two-turn case.
- Each set file ends with an approved substitution list, `{"approved": [["mattpocock-skills:diagnosing-bugs",
  "diagnose"], ...]}`. A pick counts as right if it is in `expected`, or if it is a canonical skill whose
  substitution for an expected skill is on the list.
- M0a maps expected names that do not exist in `~/Code` to the names that do, and Max approves each
  substitution. The `grilling` and `grill-me` to `brainstorming` substitutions are not approved: they are
  different workflows, and labels keep them apart.

### Parity (G2a)

The probe's saved runs keep only the top 8 of each answer. M1 records full Jev responses once with
`jev-1.13.0` for the 105 prompts against the probe listing, and runs the probe's decision code on the same
responses. `jevroute eval --responses` must then give the same per-prompt decision for every prompt. The
built requests are compared field by field with the probe's.

### Live and fresh sets (G2b, G3)

- G2b: live `jevroute eval` on the 105 prompts against the probe listing fixture. The target is a band (97 or
  more right, 0 wrong, 0 needless) because two routes to the same model on the same day disagreed on 1 of 105
  tops and moved scores by up to 0.09.
- G3: 100 prompts written by a separate agent from the listing of a `~/Code` session. At least two repos, short
  follow-ups, lookalikes, prompts that separate the members of each group, and at least 10 prompts with 1,000
  or more characters of pasted logs, stack traces, code or terminal output, some with the request before the
  paste and some after. Labels and class balance are committed before the first run.
- A new Jev model id repeats both: refit the threshold on the 105 development prompts, then accept on a set
  that was not used for the refit. The cut belongs to the model, not to the task.

## M0 procedure

### M0a - groundwork

1. A logging hook in a scratch `~/Code` project writes, on each call, whether `transcript_path` exists and
   whether it holds a `skill_listing` entry. Run one interactive session with two prompts and one `claude -p`
   run. Record the Claude Code version.
2. Copy `prompts.jsonl`, `heldout.jsonl`, `frozen-v1.json` and the probe listing into `eval/` after a secret
   scan. Extract the listing from the probe transcript into a fixture, since Claude Code deletes old
   transcripts.
3. Map expected names to `~/Code` names, write the approved substitution list, and get Max's approval.
4. Write the 10 two-turn cases and the task rubrics for the 10 completion prompts.

### M0b - behaviour test

- Scratch repo `~/Code/jevroute-eval` with a small module and fixture files, so that prompts about code have
  something to act on.
- Three arms, each a project-level hook in its own settings file:
  - A: no hook.
  - B: a fixed reminder: "Before you start, check whether one of the listed skills fits this request, and load
    it with the Skill tool if it does."
  - C: a throwaway Python hook that implements the PRD pipeline with `jev-1.13.0`, including the short-reply
    skip and the project listing fallback. One warm-up session seeds the project listing.
- Run: `claude -p --output-format stream-json --max-turns 3`, tools limited to `Skill`, `Read`, `Glob`,
  `Grep`. Two-turn cases use `--resume` for the second prompt, so the second prompt runs with its session's
  own listing. Only the second prompt is scored.
- Controls:
  - The Claude model is passed as an explicit versioned id, and the settings files are frozen and hashed into
    the results.
  - Every trial starts a fresh session, and the worktree is reset between trials.
  - Arms are interleaved case by case (A, B, C, then the next case, rotating the start arm), so drift in
    time or service load spreads across the arms.
- Harness validation first: 6 cases (2 skill, 2 no-skill, 2 two-turn) x 3 arms x 1 run. Check that every
  `Skill` call is parsed, the hook arms fire, and a reset leaves the worktree clean.
- Baseline pilot second: arm A alone, once per skill case (75 calls, the two-turn cases with their setup
  prompt). If Claude already uses the right skill on 68 or more of the 75, G1a (+10 points) cannot be met
  and the project stops here. The pilot run counts as the first of arm A's three runs in the full run, so
  nothing is wasted when the pilot passes. Only then start the full run.
- Volume:
  - Scored case trials: 115 cases x 3 arms x 3 runs = 1,035.
  - Setup prompts for the two-turn cases: 10 x 3 x 3 = 90 more `claude -p` calls.
  - Completion runs: 10 prompts x 2 arms = 20.
  - Harness validation: 18.
  - Total: about 1,160 `claude -p` calls.
- Aggregation, as in PRD G1:
  - Every run-level result is kept in `eval/runs/`.
  - A case is correct when at least 2 of its 3 runs are correct.
  - A case's unwanted-load count is the median of its 3 runs.
  - Arm totals are sums over cases.
- From the stream: every `Skill` tool call, its result, and the time to the first assistant output.
- Completion: 10 skill prompts run to the end in a throwaway worktree with write tools on, arms A and C. A
  blind Claude judge scores each pair against the prompt's rubric: better, same or worse. Max reviews every
  "worse" judgement before G1e is decided.

## Testing

- Unit: `scrub` table; `roster` (full listing, delta, repeated name, name-only entry, partial last line,
  offset resume, replaced transcript, zero-parse `error:roster`); `policy` (config validation, glob exclusion,
  exclusion before groups, group sum, missing canonical, threshold edges, prompt cap at 3,999, 4,000 and
  4,001 characters with a multi-byte character at the boundary, request size cap); `provider` (resolution
  order, unknown id, built-in defaults overridden field by field, Keychain item name per provider); `scope` (allowlist, symlinks,
  parent `.jevroute-off`, env); `prompt` (slash, empty, short-reply table); `hookio` round trip.
- Replay: G2a and G2b as above. G2b is run on the provider the trial will use; a provider switch after M2
  repeats G2b on the new one.
- Failure tests, each giving exit 0, no output and the right outcome class: cold cache, locked Keychain,
  binary not granted, network down (unroutable endpoint), 8 parallel calls on one session and one project,
  oversized stdin, deadline of 50 ms.
- Latency: an external harness launches the binary and times it to process exit, on the fresh set and on
  each failure case (G4a-c).

## Known limits

- A skill removed mid-session stays in the roster until a new `isInitial: true` entry arrives.
- The project listing can lag behind a skill added in another session. The 7-day age limit bounds staleness
  but does not prove that a stored skill exists in the new session (for example a project-level skill that
  exists on one worktree's branch only).
- A dropped project-cache write (lock busy for 20 ms) leaves the older listing in place until the next prompt.
- Free text (addresses, case or medical details) is not scrubbed; the allowlist is the control.
