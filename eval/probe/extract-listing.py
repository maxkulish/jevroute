#!/usr/bin/env python3
"""Rebuild listing.jsonl (not committed) from the probe session's transcript.

    python3 eval/probe/extract-listing.py ~/.claude/projects/<project>/<session>.jsonl eval/probe/listing.jsonl

Keeps the skill_listing attachments (type, isInitial, skillCount, names, content) with the Claude Code
version and timestamp; drops session, cwd and uuid fields.
"""
import json
import sys

src, dst = sys.argv[1], sys.argv[2]
out = []
for line in open(src):
    try:
        o = json.loads(line)
    except ValueError:
        continue
    a = o.get("attachment")
    if isinstance(a, dict) and a.get("type") == "skill_listing":
        out.append({"type": "attachment", "version": o.get("version"), "timestamp": o.get("timestamp"),
                    "attachment": {k: a[k] for k in ("type", "isInitial", "skillCount", "names", "content") if k in a}})
open(dst, "w").write("".join(json.dumps(e) + "\n" for e in out))
print(f"{len(out)} listing entries -> {dst}")
