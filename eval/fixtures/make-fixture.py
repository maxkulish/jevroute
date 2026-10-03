#!/usr/bin/env python3
"""Turn a Claude Code session transcript into a parser fixture (CLO-835).

Keeps every line, its type, uuids, timestamps, cwd and version, so batch order and the position of
the skill_listing entries are preserved. Keeps the full attachment only for skill_listing and the
hook_success entries of the probe hook; every other attachment (instructions, session_context,
environment, model, ...) is reduced to its type, because they carry the user's own files. Other
record types (system, cost-state, file-history-snapshot, ...) keep type and timestamp only.

    python3 eval/fixtures/make-fixture.py <transcript.jsonl> eval/fixtures/code-transcript.jsonl
"""
import json
import sys

KEEP_TOP = ("parentUuid", "isSidechain", "type", "uuid", "timestamp", "sessionId", "version", "cwd",
            "gitBranch", "userType", "entrypoint", "isMeta")
KEEP_ATTACHMENT = {"skill_listing", "hook_success", "hook_additional_context"}
HOOK_NAME = "log-listing.sh"


def reduce(o):
    out = {k: o[k] for k in KEEP_TOP if k in o}
    t = o.get("type")
    if t == "attachment":
        a = o["attachment"]
        if a.get("type") == "skill_listing":
            out["attachment"] = a
        elif a.get("type") in KEEP_ATTACHMENT and HOOK_NAME in json.dumps(a):
            out["attachment"] = {"type": a["type"], "hookName": "UserPromptSubmit", "redacted": True}
        else:
            out["attachment"] = {"type": a.get("type"), "redacted": True}
    elif t in ("user", "assistant"):
        m = o.get("message", {})
        out["message"] = {"role": m.get("role"), "content": m.get("content")}
    else:
        out["redacted"] = True
    return out


def main(src, dst):
    n = 0
    with open(dst, "w") as fh:
        for line in open(src):
            try:
                o = json.loads(line)
            except ValueError:
                continue
            fh.write(json.dumps(reduce(o)) + "\n")
            n += 1
    print(f"{n} lines -> {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
