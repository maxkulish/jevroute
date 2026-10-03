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
