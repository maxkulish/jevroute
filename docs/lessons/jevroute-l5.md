---
id: jevroute-l5
kind: gotcha
scope: [eval/probe/listing.jsonl, eval/fixtures/code-transcript.jsonl]
evidence: [PR #5 of the pre-rewrite repo untracked both files; git pull --ff-only removed them from the working tree]
learned_at_commit: 1e4a3d93815c7c2883d95089e17677775a63c2d8
last_verified_commit: 1e4a3d93815c7c2883d95089e17677775a63c2d8
status: active
supersedes: null
---

# A fast-forward pull deletes files the new commit untracks

When a branch stops tracking a file and the local checkout fast-forwards onto that commit, git removes the working copy even if the file is now gitignored. Local-only inputs that a PR untracks disappear from the machine that pulls it.

How to apply: before pulling a commit that untracks a local-only input, copy the file aside or keep a bundle of the last tracked version, then restore it after the pull.
