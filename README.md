# jevroute

A small Rust CLI that runs as a Claude Code `UserPromptSubmit` hook. For each prompt in an allowed
project it asks TypeSafe's Jev model which skill fits, and adds a one-line hint only when the model is
confident. Claude's own skill listing stays unchanged, so a missed hint costs nothing and a wrong hint is
the one error the project is built to avoid.

## Status

**Stopped on 3 Oct 2026.** The behaviour test's baseline pilot showed Claude Code loading the right skill
on 69 of 75 cases with no hint at all, which met the project's own stop rule (68 or more), so no binary
was built. The reasoning and the numbers are in
[docs/findings/2026-10-03-baseline-pilot-stop.md](docs/findings/2026-10-03-baseline-pilot-stop.md).
The documents and evaluation data stay as reference; [docs/PROJECT.md](docs/PROJECT.md) and
[docs/ROADMAP.md](docs/ROADMAP.md) show where the gated plan ended.

## Layout

| Path | What it holds |
|------|---------------|
| `docs/prd/` | Product requirements (v3) |
| `docs/design/` | Design: request shape, scrub rules, roster handling, decision rule |
| `docs/findings/` | Short write-ups of things measured along the way |
| `eval/probe/` | 105 probe prompts, the frozen config, saved runs and recorded Jev responses |
| `eval/fixtures/` | Transcript fixture builder for the hook's parser |
| `scripts/` | Repo checks |

## Evaluation data

`eval/probe/record.py --score` grades the recorded responses offline from the files in the repo.
`--check` and `--record` need two local files that are deliberately not committed: the skill listing the
prompts were scored against and an alias map for skill names. `eval/probe/README.md` explains the
provenance of every file and how the scores were produced.

## License

MIT, see [LICENSE](LICENSE).
