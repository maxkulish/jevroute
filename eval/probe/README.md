# Probe eval data (CLO-836)

Prompt sets, config, saved runs and the exact skill listing of the September 2026 probe, copied from
`~/Work/investigations/typesafe/experiments/skill-suggestion/` on 2 October 2026. Labels use the names of
that listing (an `~/Work/investigations` session), not `~/Code` names; the `~/Code` label set lives in
`eval/code/` (CLO-838). Nothing in this folder is edited after import, except `heldout.jsonl` q04, where a home path became `~/` (the probe's scrub sent it that way).

| File | Source | Content |
|---|---|---|
| `prompts.jsonl` | `prompts.jsonl` | 55 development prompts, `expected` lists every acceptable probe name |
| `heldout.jsonl` | `heldout.jsonl` | 50 second-set prompts written by a separate agent |
| `frozen-v1.json` | `frozen-v1.json` | the frozen pipeline: `jev-latest`, threshold 0.9, exclusions, groups |
| `runs/frozen-frozen-v1-prompts.jsonl` | `runs/` (gitignored there) | saved run of 29 Sep 2026: top 8 of the ranking, `pick`, `top`, `score` |
| `runs/frozen-frozen-v1-heldout.jsonl` | `runs/` | same for the second set |
| `listing.jsonl` (not committed) | transcript `89cac098-a040-45d3-95e4-ca4e9e2abe78` via `extract-listing.py` | the two `skill_listing` attachments of the probe session (Claude Code 2.1.284): the `isInitial` entry of 150 skills and one delta adding `test-audit`. Kept out of this public repo because skill names and descriptions describe the owner's work and home projects; rebuild it locally with `extract-listing.py` |

Merged, the listing holds 151 skills; `frozen-v1.json` exclusions leave 138 eligible. The disk-built
roster the probe rejected (`runs/listing.txt`) is not imported.

## Rescore without group widening

`probe.py` graded a pick as right when it was in `expected + canon(expected)`, so a group substitution
could pass. `rescore.py` grades against `expected` only:

```
$ python3 eval/probe/rescore.py
prompts (55): {'right': 53, 'wrong': 0, 'needless': 0, 'missed': 2}
    p19 missed pick=None top=wrangler score=0.51
    p31 missed pick=None top=superpowers:brainstorming score=0.71
heldout (50): {'right': 46, 'wrong': 0, 'needless': 0, 'missed': 4}
    q12 missed pick=None top=turnstile-spin score=0.46
    q16 missed pick=None top=cloudflare score=0.52
    q34 missed pick=None top=sandbox-migrate-to-next score=0.88
    q44 missed pick=None top=anthropic-skills:xlsx score=0.79
```

The numbers equal the probe's 53/55 and 46/50, so no saved pick relied on the widening. All six errors
are misses below the 0.9 threshold.

trufflehog 3.97.9 filesystem scan of this folder on import: 0 verified, 0 unverified secrets.

## Recorded jev-1.13.0 requests and responses (CLO-837)

`record.py` rebuilds the probe request with `model: jev-1.13.0` instead of the moving `jev-latest` alias
and saves, per prompt, the request's model and scrubbed prompt plus a SHA-256 of its `questions`, and the
full response, in `recorded/<id>.json` (105 files, recorded 3 Oct 2026, no header or key in them). The
`questions` object itself (every skill name and description) is not committed; `record.py --check` rebuilds
it from the local `listing.jsonl` and asserts its hash equals the one in all 105 files. Three skill names in the
local roster are personal; `record.py` renames them through a local `aliases.json` (not committed, a list of
`[regex, replacement]` pairs) before it builds the request, so every committed file, including the saved runs
and the recorded responses, carries the alias and the hash covers the aliased names. `recorded/decisions.jsonl` holds the frozen decision on each
recorded response next to the saved jev-latest pick. `record.py --check` asserts that the design's tightened
scrub leaves every name and description of the listing unchanged; the probe's own scrub would have altered
`audit-prompt-caching` and `claude-api`.

```
$ python3 eval/probe/record.py --score
prompts (55): right 53, wrong 0, needless 0, missed 2, http p50 287 ms p90 344 ms
    p19 missed pick=None top=wrangler score=0.51
    p31 missed pick=None top=superpowers:brainstorming score=0.71
  decisions that differ from the saved jev-latest run: 0
heldout (50): right 45, wrong 0, needless 1, missed 4, http p50 289 ms p90 316 ms
    q12 missed pick=None top=turnstile-spin score=0.43
    q16 missed pick=None top=cloudflare score=0.55
    q34 missed pick=None top=sandbox-migrate-to-next score=0.88
    q44 missed pick=None top=anthropic-skills:xlsx score=0.79
    q47 needless pick=grafana-logs top=grafana-logs score=0.91
  decisions that differ from the saved jev-latest run: 2
    q39 now pick=None top=superpowers:requesting-code-review 0.50 | saved pick=None top=none 0.48
    q47 now pick=grafana-logs top=grafana-logs 0.91 | saved pick=None top=grafana-logs 0.87
```

One decision changed against the 29 Sep run. `q47` ("tail the build log and tell me the last error",
expected no skill) scored `grafana-logs` at 0.87 on 29 Sep and 0.91 in this recording. Five more calls on
3 Oct gave 0.90, 0.88, 0.89, 0.87, 0.87, so the prompt sits on the 0.9 threshold and the pinned model is not
deterministic within about 0.02. The recorded response is kept as it came back. For the offline parity check
(G2a) this is harmless, since the decision is computed from the recorded response. For the live replay
(G2b, "0 needless") it means one boundary prompt can flip a run; the candidate skill is also a wrong one for
a local build log. Noted on CLO-856.
