# jevroute Roadmap

**Last Updated**: 2026-10-03

**Project stopped on 3 Oct 2026** at the M0b baseline pilot: 69 of 75 right without a hook against a stop
rule of 68 or more ([finding](./findings/2026-10-03-baseline-pilot-stop.md)). Every task below that is not
Done was cancelled in Linear with that reason.

Phases are the Linear milestones. Each is a gate: it passes when its reports show the goals met, not when
its issues are closed ([PRD section 10](./prd/2026-09-29-jevroute-prd.md)).

---

## Phase M0a: Groundwork

No pass/fail gate. Exit: findings recorded, eval data and fixtures in the repo.

| Task | Title | Status | Dependencies |
|------|-------|--------|--------------|
| CLO-835 | Check whether the first prompt's hook sees a skill listing and save a ~/Code transcript fixture | Done | - |
| CLO-836 | Import the probe eval data and rescore its saved picks without group widening | Done | - |
| CLO-837 | Record full jev-1.13.0 responses and requests for the 105 probe prompts | Done | CLO-836 |
| CLO-838 | Relabel expected skills to ~/Code names and approve substitutions | Cancelled | CLO-835, CLO-836 |
| CLO-839 | Write the 10 two-turn cases and the 10 completion rubrics | Cancelled | CLO-835, CLO-838 |

---

## Phase M0b: Behaviour test

Gate G1. Baseline pilot first: 68 or more of 75 right in the no-hook arm stops the project. No product code before this passes.

| Task | Title | Status | Dependencies |
|------|-------|--------|--------------|
| CLO-840 | Build the throwaway Jev hook for the behaviour test's arm C | Cancelled | CLO-835, CLO-836 |
| CLO-841 | Validate the three-arm behaviour harness on 6 cases | Cancelled | CLO-838, CLO-839, CLO-840 |
| CLO-863 | Run the no-hook baseline pilot on the 75 skill cases and decide whether M0b continues | Done, stop rule met | CLO-841 |
| CLO-842 | Run the full behaviour test and report G1a-d with the stop rule | Cancelled | CLO-841, CLO-863 |
| CLO-843 | Run the 10 completion prompts, judge them blind, and review the worse cases | Cancelled | CLO-841 |

---

## Phase M1: Binary

Gate G2a: `jevroute eval --responses` gives the probe's decision on every one of the 105 prompts.

| Task | Title | Status | Dependencies |
|------|-------|--------|--------------|
| CLO-844 | Tracer: jevroute hook adds a Jev hint from a scrubbed prompt and logs one outcome line | Cancelled | CLO-842, CLO-843 |
| CLO-845 | Add jevroute key for per-provider Keychain access that never shows a dialog | Cancelled | CLO-844 |
| CLO-846 | Keep the hook silent outside allowed folders and on slash commands and short replies | Cancelled | CLO-844 |
| CLO-847 | Combine near-duplicate skills into one hint | Cancelled | CLO-844 |
| CLO-848 | Scrub skill names and descriptions in the outbound request | Cancelled | CLO-844 |
| CLO-849 | Give hints for a skill added mid-session from the next prompt | Cancelled | CLO-844 |
| CLO-850 | Stop the hook at 750 ms without ever emitting a partial hint | Cancelled | CLO-844 |
| CLO-851 | Keep an opt-in local sample of up to 30 turns for the M3 review | Cancelled | CLO-844 |
| CLO-852 | Give a new worktree's first prompt a hint from the project listing | Cancelled | CLO-849 |
| CLO-853 | Make jevroute eval reproduce the probe's decision on every prompt | Cancelled | CLO-837, CLO-846, CLO-847, CLO-848, CLO-849 |
| CLO-854 | Add jevroute doctor to report readiness, the provider in use and a model alias | Cancelled | CLO-845, CLO-846, CLO-852, CLO-864 |
| CLO-864 | Add jevroute provider to choose between TypeSafe and OpenRouter and save the choice | Cancelled | CLO-844, CLO-845 |

---

## Phase M2: Acceptance

Gates G2b (97 or more of 105 right, 0 wrong, 0 needless), G3 (100 fresh prompts) and G4a-c, on one frozen build and one provider.

| Task | Title | Status | Dependencies |
|------|-------|--------|--------------|
| CLO-855 | Write and freeze the fresh 100-prompt acceptance set | Cancelled | CLO-835, CLO-838 |
| CLO-856 | Pass the live replay on the 105 probe prompts with the frozen acceptance build | Cancelled | CLO-844 to CLO-853, CLO-864 |
| CLO-857 | Build the external timing harness and pass the failure matrix on development fixtures | Cancelled | CLO-844 to CLO-853, CLO-856 |
| CLO-858 | Run the fresh acceptance set once through the timing harness and report G3 and G4a | Cancelled | CLO-853, CLO-855, CLO-856, CLO-857 |

---

## Phase M3: One-week trial

Keep if G4d holds, `error:roster` never occurs, and at most 1 judged hinted turn steered Claude wrong. Otherwise remove.

| Task | Title | Status | Dependencies |
|------|-------|--------|--------------|
| CLO-859 | Install the accepted jevroute build as a user-level hook for the one-week trial | Cancelled | CLO-851, CLO-854, CLO-856, CLO-857, CLO-858 |
| CLO-860 | Decide whether to keep or remove jevroute after the one-week trial | Cancelled | CLO-859 |

---

## Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| M0a: Groundwork | 5 | 3 | Closed, 2 cancelled |
| M0b: Behaviour test | 5 | 1 | Closed, stop rule met, 4 cancelled |
| M1: Binary | 12 | 0 | Cancelled |
| M2: Acceptance | 4 | 0 | Cancelled |
| M3: One-week trial | 2 | 0 | Cancelled |
