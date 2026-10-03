# Finding: the first prompt's hook runs before the skill listing exists

Date: 2026-10-03. Claude Code 2.1.288 (one run on 2.1.287). Issue: CLO-835. Closes PRD open question 1.

## Question

When `UserPromptSubmit` fires on a session's first prompt, does `transcript_path` already hold a
`skill_listing` entry? jevroute reads the roster from that entry (design, Roster), so the answer decides
whether a first prompt can get a hint from the session itself or only from the project fallback (F5a).

## Method

A scratch project `~/Code/jevroute-probe` with a project-level `UserPromptSubmit` hook that appends one
line per call: whether `transcript_path` exists, its line count, whether it holds `"skill_listing"`, and the
`isInitial` values. Three sessions:

| Session | How | Prompt 1 | Prompt 2 |
|---|---|---|---|
| `972c0ecc` (2.1.287) | `claude -p`, one prompt | no transcript file | - |
| `16455f35` | `claude -p`, then `claude -p --resume` | no transcript file | transcript of 35 lines, `skill_listing` present, `isInitial: true` |
| `81c79b46` | interactive `claude` driven through a pty (`entrypoint=cli`), two prompts | no transcript file | transcript of 39 lines, `skill_listing` present, `isInitial: true` |

In session `81c79b46` the hook's own `hook_success` entry carries 10:07:25.384; the first user message and
the `skill_listing` (`isInitial: true`, 130 skills) both carry 10:07:27.470, written in one batch 2.1 s after
the hook ran. Session `972c0ecc` shows the same order with 1.1 s between them.

## Answer

- First prompt: the hook cannot see the listing. The transcript file does not exist yet; the listing is
  written together with the first user message after the hooks finish. A first-prompt hint can only come
  from the project fallback (F5a), and an unknown project gives `skip:roster`.
- Second prompt onward: the transcript exists and holds the `isInitial: true` listing, so the in-session
  path works from the second prompt.

## Also observed

- A `claude` started from inside another Claude Code session inherits `CLAUDE_CODE_CHILD_SESSION` and shows
  "Transcript saving is off". Its hooks never see a transcript, so jevroute would give `skip:roster` on every
  prompt of such a nested session. Clearing `CLAUDE_*` from the environment restores saving.
- The `~/Code` listing of this scratch project has 130 skills interactively and 126 under `claude -p`; the
  `~/Work/investigations` probe listing has 151. Skill counts are per project and per entrypoint.

## Fixture

`eval/fixtures/code-transcript.jsonl` (not committed; rebuilt locally with `make-fixture.py`, the `~/Code` listing
names the owner's work and home projects) is session `81c79b46` reduced by `eval/fixtures/make-fixture.py`: every
line, type, uuid, timestamp, cwd and version is kept, the `skill_listing` attachment is kept in full, every
other attachment and record is reduced to its type because the raw transcript carries the user's own
instruction and memory files. trufflehog 3.97.9: 0 verified, 0 unverified.
