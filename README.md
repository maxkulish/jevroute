# jevroute

A small Rust CLI that runs as a Claude Code `UserPromptSubmit` hook. For each prompt in an allowed
project it asks TypeSafe's Jev model which skill fits, and adds a one-line hint only when the model is
confident. Claude's own skill listing stays unchanged, so a missed hint costs nothing and a wrong hint is
the one error the project is built to avoid.

## Status

Documents and evaluation data only; the binary is not written yet. Work proceeds through gated
milestones (groundwork, behaviour test, binary, acceptance, one-week trial). The current state is in
[docs/PROJECT.md](docs/PROJECT.md) and [docs/ROADMAP.md](docs/ROADMAP.md).

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
