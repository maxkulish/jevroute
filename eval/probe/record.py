#!/usr/bin/env python3
"""Record full jev-1.13.0 requests and responses for the 105 probe prompts (CLO-837).

Builds the probe's request exactly (frozen-v1.json instructions, one option per eligible skill from
listing.jsonl, the none option, the probe's scrub on the prompt) with the pinned model instead of
jev-latest, saves request and response per prompt in recorded/, runs the frozen decision on each
response and diffs it against the saved jev-latest picks.

    python3 eval/probe/record.py            # record (skips prompts already in recorded/), then score
    python3 eval/probe/record.py --score    # score only
    python3 eval/probe/record.py --check    # assert the tightened scrub leaves the listing unchanged

The API key is read with `op read` and kept in memory only.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REC = HERE / "recorded"
MODEL = "jev-1.13.0"
URL = os.environ.get("JEV_URL", "https://api.typesafe.ai/v1/systemone")
KEY_REF = os.environ.get("JEV_KEY_REF", "")  # op://<vault>/<item>/<field>, or env:<VAR>
SETS = {"prompts": "frozen-frozen-v1-prompts.jsonl", "heldout": "frozen-frozen-v1-heldout.jsonl"}

# The probe's scrub (probe.py SCRUB), unchanged, so the recorded request equals the probe's.
SCRUB_PROBE = [
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----", "[KEY]"),
    (r"\b(sk|csk|gsk|xai|pplx|ghp|gho|ghs|github_pat|glpat|hf|xox[abpr]|op)[-_][A-Za-z0-9_\-]{12,}", "[KEY]"),
    (r"\bAKIA[0-9A-Z]{16}\b", "[KEY]"),
    (r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}", "[JWT]"),
    (r"(?i)\b(bearer|token|password|passwd|secret|api[_-]?key)\b\s*[:=]?\s*\S{8,}", r"\1 [REDACTED]"),
    (r"\b[A-Z]{2}\d{2}[A-Z]{4}\d{10}\b", "[IBAN]"),
    (r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", "[EMAIL]"),
    (r"(?<!\d)(\+31|0031|0)[\s\-]?[1-9](?:[\s\-]?\d){8}(?!\d)", "[PHONE]"),
    (r"(?<![\d.])\d{9}(?![\d.])", "[NUMBER]"),
    (r"\b[0-9a-f]{32,}\b", "[HEX]"),
    (r"[A-Za-z0-9+/_\-]{40,}={0,2}", "[BLOB]"),
    (r"/Users/[A-Za-z0-9_\-]+", "~"),
]
# The design's tightened rules: the keyword rule needs `:` or `=`, the blob rule needs two digits
# (design, Scrub). Everything else is the probe's.
SCRUB_TIGHT = [
    (p, r) for p, r in SCRUB_PROBE
    if not p.startswith("(?i)") and not p.startswith("[A-Za-z0-9+/_")
]
SCRUB_TIGHT[4:4] = [(r"(?i)\b(bearer|token|password|passwd|secret|api[_-]?key)\b\s*[:=]\s*\S{8,}", r"\1 [REDACTED]")]
SCRUB_TIGHT.insert(-1, (r"(?=[A-Za-z0-9+/_\-]*\d[A-Za-z0-9+/_\-]*\d)[A-Za-z0-9+/_\-]{40,}={0,2}", "[BLOB]"))


def scrub(text, rules):
    for p, r in rules:
        text = re.sub(p, r, text)
    return text


def load(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def listing():
    """Merged roster from listing.jsonl: isInitial replaces, later entries add or update by name."""
    skills = {}
    for e in load(HERE / "listing.jsonl"):
        a = e["attachment"]
        if a.get("isInitial"):
            skills = {}
        cur = None
        for line in a["content"].split("\n"):
            m = re.match(r"^- (\S+?)(?::\s(.*))?$", line.rstrip())
            if m:
                cur = m.group(1)
                skills[cur] = (m.group(2) or "").strip()
            elif cur and line.strip():
                skills[cur] = f"{skills[cur]} {line.strip()}".strip()
    return skills


def config():
    cfg = json.loads((HERE / "frozen-v1.json").read_text())
    listed = listing()
    excl = [re.compile("^" + re.escape(p).replace(r"\*", ".*") + "$") for p in cfg["exclude"]]
    eligible = {n: d for n, d in listed.items() if not any(x.match(n) for x in excl)}
    canon = {}
    for target, members in cfg["groups"].items():
        if target not in eligible:
            raise SystemExit(f"group target {target} is not in the eligible listing")
        for m in members:
            if m in eligible:
                canon[m] = target
    return cfg, listed, eligible, canon


def questions(cfg, eligible):
    crit = {n: d or f"A skill named {n}." for n, d in eligible.items()}
    crit["none"] = cfg["none"]
    return {"which": {"type": "choice", "instructions": cfg["instructions"], "criteria": crit}}


def questions_sha256(q):
    return hashlib.sha256(json.dumps(q, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def ranked_of(resp):
    a = (resp.get("answers") or {}).get("which")
    if not a:
        return None
    probs = a.get("probabilities") or {a["choice"]: a.get("confidence") or 0}
    return sorted(probs.items(), key=lambda kv: -(kv[1] or 0))


def frozen_decide(cfg, canon, ranked):
    agg = {}
    for n, p in ranked:
        c = canon.get(n, n)
        agg[c] = agg.get(c, 0) + (p or 0)
    name, score = max(agg.items(), key=lambda kv: kv[1])
    return (name if name != "none" and score >= cfg["threshold"] else None), name, score


def grade(pick, expected):
    if not expected:
        return "right" if not pick else "needless"
    if not pick:
        return "missed"
    return "right" if pick in expected else "wrong"


def api_key():
    if not KEY_REF:
        raise SystemExit("set JEV_KEY_REF to op://<vault>/<item>/<field> or env:<VAR>")
    if KEY_REF.startswith("env:"):
        return os.environ[KEY_REF[4:]]
    return subprocess.check_output(["op", "read", KEY_REF], text=True).strip()


def call(key, body, attempts=4):
    """POST once; retry connection errors, timeouts, 429 and 5xx with 1, 2, 4 s backoff."""
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json", "authorization": f"Bearer {key}"})
    t = time.time()
    for i in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read()), int((time.time() - t) * 1000)
        except urllib.error.HTTPError as e:
            status, out = e.code, {"error": e.code, "body": e.read().decode(errors="replace")[:500]}
            if status != 429 and status < 500:
                return status, out, int((time.time() - t) * 1000)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            status, out = 0, {"error": type(e).__name__, "body": str(e)[:500]}
        if i + 1 < attempts:
            time.sleep(2 ** i)
    return status, out, int((time.time() - t) * 1000)


def recorded_ok(path):
    """A fixture counts as recorded only if it parses and holds a 200 response."""
    try:
        rec = json.loads(path.read_text())
    except (OSError, ValueError):
        return False
    return rec.get("status") == 200 and "response" in rec and "request" in rec


def cmd_record(workers):
    cfg, _, eligible, _ = config()
    q = questions(cfg, eligible)
    REC.mkdir(exist_ok=True)
    todo = []
    for name in SETS:
        for p in load(HERE / f"{name}.jsonl"):
            if not recorded_ok(REC / f"{p['id']}.json"):
                todo.append(p)
    print(f"eligible {len(eligible)}, to record {len(todo)}")
    if not todo:
        return
    key = api_key()

    def one(p):
        body = {"model": MODEL, "state": {"request": scrub(p["prompt"], SCRUB_PROBE), "recent_context": ""},
                "questions": q}
        status, resp, ms = call(key, body)
        # The committed request carries the model, the scrubbed prompt and a hash of the questions; the
        # questions themselves (every skill name and description) stay out of the public repo and are
        # rebuilt from listing.jsonl, which is not committed either.
        kept = {"model": body["model"], "state": body["state"], "questions_sha256": questions_sha256(q)}
        rec = {"id": p["id"], "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "status": status, "ms": ms, "request": kept, "response": resp}
        if status == 200:
            tmp = REC / f"{p['id']}.json.tmp"
            tmp.write_text(json.dumps(rec, indent=1) + "\n")
            os.replace(tmp, REC / f"{p['id']}.json")
        return p["id"], status, ms

    failed = []
    with cf.ThreadPoolExecutor(workers) as ex:
        for pid, status, ms in ex.map(one, todo):
            print(f"  {pid} {status} {ms} ms")
            if status != 200:
                failed.append(pid)
    if failed:
        raise SystemExit(f"{len(failed)} prompt(s) not recorded after retries: {' '.join(failed)}. "
                         "Run again to record only those; nothing is scored until all 105 exist.")


def cmd_score():
    cfg, _, _, canon = config()
    out, lines = [], []
    for name, run in SETS.items():
        prompts = load(HERE / f"{name}.jsonl")
        saved = {r["id"]: r for r in load(HERE / "runs" / run)}
        c = {"right": 0, "wrong": 0, "needless": 0, "missed": 0}
        diffs, bad, ms = [], [], []
        for p in prompts:
            f = REC / f"{p['id']}.json"
            if not f.exists():
                raise SystemExit(f"{p['id']} not recorded")
            rec = json.loads(f.read_text())
            ranked = ranked_of(rec["response"]) or []
            pick, top_name, score = frozen_decide(cfg, canon, ranked) if ranked else (None, None, 0)
            g = grade(pick, p["expected"])
            c[g] += 1
            ms.append(rec["ms"])
            s = saved[p["id"]]
            d = {"id": p["id"], "set": name, "pick": pick, "top": top_name, "score": round(score, 4),
                 "grade": g, "ranked": ranked[:8], "ms": rec["ms"],
                 "saved_pick": s["pick"], "saved_top": s["top"], "saved_score": s["score"]}
            out.append(d)
            if g != "right":
                bad.append(f"    {p['id']} {g} pick={pick} top={top_name} score={score:.2f}")
            if pick != s["pick"] or top_name != s["top"]:
                diffs.append(f"    {p['id']} now pick={pick} top={top_name} {score:.2f} | saved pick={s['pick']} top={s['top']} {s['score']:.2f}")
        ms.sort()
        lines.append(f"{name} ({len(prompts)}): {c}, http p50 {ms[len(ms)//2]} ms p90 {ms[int(len(ms)*0.9)]} ms")
        lines += bad
        lines.append(f"  decisions that differ from the saved jev-latest run: {len(diffs)}")
        lines += diffs
    (REC / "decisions.jsonl").write_text("".join(json.dumps(d) + "\n" for d in out))
    print("\n".join(lines))
    return lines


def cmd_check():
    _, listed, _, _ = config()
    raw = "".join(e["attachment"]["content"] for e in load(HERE / "listing.jsonl"))
    changed = [n for n, d in listed.items() if scrub(n, SCRUB_TIGHT) != n or scrub(d, SCRUB_TIGHT) != d]
    assert scrub(raw, SCRUB_TIGHT) == raw and not changed, f"tightened scrub changes the listing: {changed[:5]}"
    loose = [n for n, d in listed.items() if scrub(n, SCRUB_PROBE) != n or scrub(d, SCRUB_PROBE) != d]
    print(f"tightened scrub: listing of {len(listed)} skills unchanged; the probe's scrub would change {len(loose)}: {loose}")
    cfg, _, eligible, _ = config()
    h = questions_sha256(questions(cfg, eligible))
    rec = {json.loads(f.read_text())["request"].get("questions_sha256") for f in REC.glob("*.json")}
    assert rec == {h}, f"recorded questions hash {rec} != current listing {h}"
    print(f"questions hash {h[:12]} matches all {len(list(REC.glob('*.json')))} recorded requests")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    if a.check:
        cmd_check()
    elif a.score:
        cmd_score()
    else:
        cmd_record(a.workers)
        cmd_score()
