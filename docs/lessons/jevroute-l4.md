---
id: jevroute-l4
kind: gotcha
scope: [git workflow]
evidence: [3 Oct 2026: git ls-remote still showed the old sha after a force-push attempt; reset --hard plus reflog expire and gc destroyed the local alias commit]
learned_at_commit: 1e4a3d93815c7c2883d95089e17677775a63c2d8
last_verified_commit: 1e4a3d93815c7c2883d95089e17677775a63c2d8
status: active
supersedes: null
---

# Never reset or gc on a push you did not watch land

A `reset --hard origin/<branch>` followed by `reflog expire` and `gc --prune=now` deletes local commits for good when the remote has not actually moved, for example when a hook blocked the push or the push ran in another session. The only recovery was a second clone.

How to apply: before any reset or gc that follows a push, run `git ls-remote origin refs/heads/<branch>` and compare the sha to local HEAD. Keep a second clone or a bundle until they match.
