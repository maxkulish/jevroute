---
id: jevroute-l2
kind: decision
scope: [eval/probe/record.py, eval/probe/aliases.json]
evidence: [eval/probe/record.py aliases() and alias(), record.py --check, questions hash bcf6e8577210]
learned_at_commit: 1e4a3d93815c7c2883d95089e17677775a63c2d8
last_verified_commit: 1e4a3d93815c7c2883d95089e17677775a63c2d8
status: active
supersedes: null
---

# Alias private skill names at the source, not per file

The recorder renames skills through a gitignored alias map before it builds the request, so prompts, recorded responses, the frozen config and the content hash all carry the alias. A per-file scrub after the fact would have left the hash tied to the real names and every later run would have had to be scrubbed again.

How to apply: when committed eval data derives from a private roster, put the renaming in the single code path that reads the roster and keep a check mode that proves the committed data matches the local map.
