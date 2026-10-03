---
id: jevroute-l3
kind: gotcha
scope: [github repository, git history rewrite]
evidence: [3 Oct 2026 rewrite: pre-rewrite shas kept resolving through refs/pull/* after the force-push; the recreated repo returns "No commit found" for them]
learned_at_commit: 1e4a3d93815c7c2883d95089e17677775a63c2d8
last_verified_commit: 1e4a3d93815c7c2883d95089e17677775a63c2d8
status: active
supersedes: null
---

# A force-push does not remove exposed blobs from GitHub

GitHub keeps pre-rewrite commits reachable through pull request refs and its object cache after a history rewrite plus force-push. For a small repo, deleting and recreating it was faster and more certain than a support purge. The cost: PR numbers restart at 1, old PR links in Linear die, and GitHub apps such as the review bot must be installed again.

How to apply: after purging sensitive content from history, verify the old shas with the commits API before declaring the exposure closed. If they still resolve, recreate the repo or file a purge request.
