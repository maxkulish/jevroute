# jevroute

## WHY

jevroute is a small Rust CLI that runs as a Claude Code `UserPromptSubmit` hook. For each prompt in an
allowed project it asks TypeSafe's Jev model which skill fits, and adds a one-line hint only when it is
confident. Claude's own skill listing stays unchanged, so a missed hint costs nothing and a wrong hint is
the one error to avoid.

- PRD: [docs/prd/2026-09-29-jevroute-prd.md](../docs/prd/2026-09-29-jevroute-prd.md)
- Design: [docs/design/2026-09-29-jevroute-design.md](../docs/design/2026-09-29-jevroute-design.md)

## Linear

Team: Cloud-ai | Team ID: 24e8554c-cce5-49ee-9ad9-3524da2e2124 | Key: CLO
Project: [jevroute](https://linear.app/cloud-ai/project/jevroute-7b0e21cf7b88) (P-CLO-7)

Each milestone is a gate: it passes when its reports show the goals met, not when its issues are closed.
Status and phases are in [docs/PROJECT.md](../docs/PROJECT.md), [docs/ROADMAP.md](../docs/ROADMAP.md)
and [docs/DEPENDENCIES.md](../docs/DEPENDENCIES.md).

## Publishing gate

The repo was public until 3 Oct 2026, when the eval data turned out to carry the owner's full skill listing
(names and descriptions that named an employer, a house purchase and home projects). The history was
rewritten and the repo made private. It is meant to become public again for distribution, so every commit
has to be publishable on its own.

Never commit:

- a skill listing, a transcript or a fixture built from one (`eval/probe/listing.jsonl`,
  `eval/fixtures/code-transcript.jsonl` and anything that embeds a `skill_listing` attachment)
- real skill names that the local `eval/probe/aliases.json` renames, or the alias file itself
- 1Password item paths, home directory paths, email addresses, or the name of an employer or a client
- a request body with its `questions` object; keep the hash, as `record.py` does

Before any push to a public remote, a visibility change, or posting an excerpt (issue, PR text, chat):

1. `scripts/privacy-check.sh` must print `clean`. It greps the tracked tree and the full history for the
   markers in `.privacy-markers.txt` (local, not committed, one string per line: employer, real skill names,
   vault items, home path, family names) and runs trufflehog on the working tree.
2. `python3 eval/probe/record.py --check` must pass, which proves the committed data uses the aliases.
3. PR descriptions and comments count as published text. Write them without the markers; a bot review that
   quotes one gets deleted, not edited.

A hit stops the push. Fix the content, do not add the marker to an allowlist.
