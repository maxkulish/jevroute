# Probe eval data (CLO-836)

Prompt sets, config, saved runs and the exact skill listing of the September 2026 probe, copied from
`~/Work/investigations/typesafe/experiments/skill-suggestion/` on 2 October 2026. Labels use the names of
that listing (an `~/Work/investigations` session), not `~/Code` names; the `~/Code` label set lives in
`eval/code/` (CLO-838). Nothing in this folder is edited after import.

| File | Source | Content |
|---|---|---|
| `prompts.jsonl` | `prompts.jsonl` | 55 development prompts, `expected` lists every acceptable probe name |
| `heldout.jsonl` | `heldout.jsonl` | 50 second-set prompts written by a separate agent |
| `frozen-v1.json` | `frozen-v1.json` | the frozen pipeline: `jev-latest`, threshold 0.9, exclusions, groups |
| `runs/frozen-frozen-v1-prompts.jsonl` | `runs/` (gitignored there) | saved run of 29 Sep 2026: top 8 of the ranking, `pick`, `top`, `score` |
| `runs/frozen-frozen-v1-heldout.jsonl` | `runs/` | same for the second set |
| `listing.jsonl` | transcript `89cac098-a040-45d3-95e4-ca4e9e2abe78` | the two `skill_listing` attachments of the probe session (Claude Code 2.1.284): the `isInitial` entry of 150 skills and one delta adding `test-audit`. Session, path and uuid fields removed |

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
