#!/usr/bin/env python3
"""Summarize a pilot results file: counts by verdict, per-case table, stop-rule bounds."""
import collections, json, pathlib, sys

p = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[1] / "runs/m0b-pilot-armA.jsonl")
rows = [d for d in map(json.loads, open(p)) if not d.get("meta")]
c = collections.Counter(r["verdict"] for r in rows)
print(len(rows), dict(c))
right, unm = c["right"], c["unmappable"]
print(f"right {right}/{len(rows)}; upper bound if the {unm} unmappable cases were right: {right + unm}; stop rule: >= 68")
print("unwanted loads on skill cases:", sum(r["unwanted_loads"] for r in rows))
for r in rows:
    got = ",".join(s["skill"] + ("" if s["ok"] else "(failed)") for s in r["scored_skill_calls"]) or "-"
    print(f"{r['id']:5} {r['verdict']:11} {got}  | exp {','.join(r['expected']) or '-'}")
