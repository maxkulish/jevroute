#!/usr/bin/env python3
"""Rescore the probe's saved frozen-v1 picks against the raw expected labels.

The probe (probe.py cmd_frozen) graded a pick as right when it was in
expected + canon(expected), which let a group substitution pass. This script
grades against expected only. Run from anywhere:

    python3 eval/probe/rescore.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SETS = {"prompts": "frozen-frozen-v1-prompts.jsonl", "heldout": "frozen-frozen-v1-heldout.jsonl"}


def grade(pick, expected):
    if not expected:
        return "right" if not pick else "needless"
    if not pick:
        return "missed"
    return "right" if pick in expected else "wrong"


def load(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def main():
    for name, run in SETS.items():
        prompts = {p["id"]: p for p in load(HERE / f"{name}.jsonl")}
        recs = load(HERE / "runs" / run)
        assert set(prompts) == {r["id"] for r in recs}, name
        c = {"right": 0, "wrong": 0, "needless": 0, "missed": 0}
        bad = []
        for r in recs:
            g = grade(r["pick"], prompts[r["id"]]["expected"])
            c[g] += 1
            if g != "right":
                bad.append(f"    {r['id']} {g} pick={r['pick']} top={r['top']} score={r['score']:.2f}")
        print(f"{name} ({len(recs)}): {c}")
        print("\n".join(bad))


if __name__ == "__main__":
    main()
