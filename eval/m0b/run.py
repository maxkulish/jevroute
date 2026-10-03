#!/usr/bin/env python3
"""M0b behaviour-test harness, arm A (no hook) only (CLO-863 pilot).

Each trial: reset the scratch worktree, run `claude -p` in a fresh session (setup turn first for a two-turn
case, then the scored prompt via --resume), parse every Skill call from the stream, classify the scored turn.

  run.py --sample            harness validation, at most 5 calls
  run.py --pilot             the 75 skill cases, arm A, run 1

Raw streams go to eval/runs/raw/ (gitignored: they hold the owner's skill listing). Per-case results go to
eval/runs/<name>.jsonl.
"""
import argparse, hashlib, json, os, pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRATCH = pathlib.Path.home() / "Code/jevroute-eval"
UNSET = ["CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_SESSION_ATTENDED",
         "CLAUDE_PID", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN",
         "CLAUDE_CODE_EXECPATH", "CLAUDE_EFFORT", "CLAUDE_GIT_BRANCH", "CLAUDE_GIT_DIRTY_FILES", "CLAUDE_PLUGIN_DATA"]
KEEP_ENV = ["CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING"]
FROZEN = {
    "model": "claude-sonnet-5-5", "effort": "medium", "max_turns": 3,
    "tools": "Skill,Read,Glob,Grep", "permission_mode": "dontAsk",
    "mcp": "none (--strict-mcp-config, empty server list)", "arm": "A (no hook)",
}
SAMPLE = ["p02", "p01", "n08", "t02"]  # 2 skill, 1 no-skill, 1 two-turn skill (2 calls) = 5 calls


def sha(p):
    p = pathlib.Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.exists() else None


def load(path):
    return [d for d in map(json.loads, open(path)) if "id" in d]


def cases():
    out = []
    for f in ("dev", "second"):
        out += [d for d in load(ROOT / f"code/{f}.jsonl") if d["expected"] or d.get("unmappable")]
    out += [d for d in load(ROOT / "code/two-turn.jsonl") if d["kind"] == "two-turn-skill"]
    return out


def all_cases():
    out = []
    for f in ("dev", "second"):
        out += load(ROOT / f"code/{f}.jsonl")
    return out + load(ROOT / "code/two-turn.jsonl")


def reset():
    env = {**os.environ, "GIT_DIR": str(SCRATCH / ".git"), "GIT_WORK_TREE": str(SCRATCH)}
    subprocess.run(["git", "reset", "-q", "--hard"], env=env, check=True)
    subprocess.run(["git", "clean", "-fdxq"], env=env, check=True)
    st = subprocess.run(["git", "status", "--porcelain"], env=env, capture_output=True, text=True).stdout
    return st.strip() == ""


def claude(prompt, resume=None):
    cmd = ["claude", "-p", "--model", FROZEN["model"], "--effort", FROZEN["effort"], "--max-turns", str(FROZEN["max_turns"]),
           "--tools", FROZEN["tools"], "--allowedTools", FROZEN["tools"].replace(",", " "),
           "--permission-mode", FROZEN["permission_mode"], "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
           "--output-format", "stream-json", "--verbose"]
    if resume:
        cmd += ["--resume", resume]
    cmd.append(prompt)
    env = {k: v for k, v in os.environ.items() if k not in UNSET}
    t = time.time()
    p = subprocess.run(cmd, cwd=SCRATCH, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300)
    return p.stdout, p.stderr, time.time() - t


def parse(stream):
    calls, results, tools, sid, res, init = [], {}, [], None, {}, {}
    for line in stream.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        t = d.get("type")
        if t == "system" and d.get("subtype") == "init":
            sid = d.get("session_id")
            init = {k: d.get(k) for k in ("model", "claude_code_version", "apiKeySource")}
            init["skills"] = len(d.get("skills") or [])
        elif t == "assistant":
            for b in d["message"]["content"]:
                if b.get("type") == "tool_use":
                    tools.append(b["name"])
                    if b["name"] == "Skill":
                        calls.append({"id": b["id"], "skill": (b["input"].get("skill") or b["input"].get("command") or "").lstrip("/")})
        elif t == "user" and isinstance(d["message"]["content"], list):
            for b in d["message"]["content"]:
                if b.get("type") == "tool_result":
                    results[b["tool_use_id"]] = not b.get("is_error", False)
        elif t == "result":
            res = {k: d.get(k) for k in ("subtype", "num_turns", "duration_ms", "total_cost_usd", "terminal_reason", "is_error")}
            sid = d.get("session_id", sid)
    for c in calls:
        c["ok"] = results.get(c.pop("id"), False)
    return {"session_id": sid, "skills": calls, "tools": tools, "result": res, "init": init}


def classify(case, setup_skills, scored):
    exp = set(case["expected"])
    calls = scored["skills"]
    loaded_before = {c["skill"] for c in setup_skills if c["ok"]}
    ok_names = {c["skill"] for c in calls if c["ok"]}
    if case.get("unmappable"):
        verdict = "unmappable"
    elif (ok_names | loaded_before) & exp:
        verdict = "right"
    elif calls:
        verdict = "wrong_skill"
    else:
        verdict = "no_skill"
    unwanted = sum(1 for c in calls if c["skill"] not in exp)
    return verdict, unwanted


def trial(case, rawdir, n):
    clean = reset()
    setup_skills, sid = [], None
    for i, s in enumerate(case.get("setup") or []):
        out, err, dt = claude(s)
        (rawdir / f"{case['id']}-setup{i}.jsonl").write_text(out)
        r = parse(out)
        setup_skills += r["skills"]
        sid = r["session_id"]
    out, err, dt = claude(case["prompt"], resume=sid)
    (rawdir / f"{case['id']}-prompt.jsonl").write_text(out)
    (rawdir / f"{case['id']}-prompt.stderr").write_text(err)
    r = parse(out)
    verdict, unwanted = classify(case, setup_skills, r)
    return {"id": case["id"], "kind": case["kind"], "run": n, "arm": "A", "expected": case["expected"],
            "verdict": verdict, "unwanted_loads": unwanted, "scored_skill_calls": r["skills"],
            "setup_skill_calls": setup_skills, "other_tools": [t for t in r["tools"] if t != "Skill"],
            "worktree_clean_before": clean, "worktree_clean_after": reset(), "seconds": round(dt, 1),
            "result": r["result"], "init": r["init"]}


def meta():
    home = pathlib.Path.home()
    ver = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    return {"meta": True, "frozen": FROZEN, "claude_version": ver, "unset_env": UNSET,
            "kept_env": {k: os.environ.get(k) for k in KEEP_ENV},
            "hashes": {"harness_run.py": sha(__file__), "user_settings.json": sha(home / ".claude/settings.json"),
                       "user_CLAUDE.md": sha(home / ".claude/CLAUDE.md"), "scratch_settings.json": sha(SCRATCH / ".claude/settings.json"),
                       "scratch_head": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=SCRATCH, capture_output=True, text=True).stdout.strip(),
                       "dev.jsonl": sha(ROOT / "code/dev.jsonl"), "second.jsonl": sha(ROOT / "code/second.jsonl"), "two-turn.jsonl": sha(ROOT / "code/two-turn.jsonl")}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--pilot", action="store_true")
    a = ap.parse_args()
    name = "m0b-sample-armA" if a.sample else "m0b-pilot-armA"
    sel = [c for c in all_cases() if c["id"] in SAMPLE] if a.sample else cases()
    sel = sorted(sel, key=lambda c: SAMPLE.index(c["id"])) if a.sample else sel
    rawdir = ROOT / "runs/raw" / name
    rawdir.mkdir(parents=True, exist_ok=True)
    outp = ROOT / f"runs/{name}.jsonl"
    done = {json.loads(l)["id"] for l in open(outp) if '"meta"' not in l} if outp.exists() else set()
    with open(outp, "a") as f:
        if not outp.stat().st_size:
            f.write(json.dumps(meta()) + "\n")
        for c in sel:
            if c["id"] in done:
                continue
            row = trial(c, rawdir, 1)
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(c["id"], row["verdict"], [s["skill"] for s in row["scored_skill_calls"]], row["seconds"], flush=True)


if __name__ == "__main__":
    main()
