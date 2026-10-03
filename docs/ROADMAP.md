# jevroute Roadmap

**Last Updated**: 2026-10-03

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
| CLO-838 | Relabel expected skills to ~/Code names and approve substitutions | Backlog | CLO-835, CLO-836 |
| CLO-839 | Write the 10 two-turn cases and the 10 completion rubrics | Backlog | CLO-835, CLO-838 |

---

## Phase M0b: Behaviour test

Gate G1. Baseline pilot first: 68 or more of 75 right in the no-hook arm stops the project. No product code before this passes.

| Task | Title | Status | Dependencies |
|------|-------|--------|--------------|
| CLO-840 | Build the throwaway Jev hook for the behaviour test's arm C | Backlog | CLO-835, CLO-836 |
| CLO-841 | Validate the three-arm behaviour harness on 6 cases | Backlog | CLO-838, CLO-839, CLO-840 |
| CLO-863 | Run the no-hook baseline pilot on the 75 skill cases and decide whether M0b continues | Backlog | CLO-841 |
| CLO-842 | Run the full behaviour test and report G1a-d with the stop rule | Backlog | CLO-841, CLO-863 |
| CLO-843 | Run the 10 completion prompts, judge them blind, and review the worse cases | Backlog | CLO-841 |

---

## Phase M1: Binary

Gate G2a: `jevroute eval --responses` gives the probe's decision on every one of the 105 prompts.

| Task | Title | Status | Dependencies |
|------|-------|--------|--------------|
| CLO-844 | Tracer: jevroute hook adds a Jev hint from a scrubbed prompt and logs one outcome line | Backlog | CLO-842, CLO-843 |
| CLO-845 | Add jevroute key for per-provider Keychain access that never shows a dialog | Backlog | CLO-844 |
| CLO-846 | Keep the hook silent outside allowed folders and on slash commands and short replies | Backlog | CLO-844 |
| CLO-847 | Combine near-duplicate skills into one hint | Backlog | CLO-844 |
| CLO-848 | Scrub skill names and descriptions in the outbound request | Backlog | CLO-844 |
| CLO-849 | Give hints for a skill added mid-session from the next prompt | Backlog | CLO-844 |
| CLO-850 | Stop the hook at 750 ms without ever emitting a partial hint | Backlog | CLO-844 |
| CLO-851 | Keep an opt-in local sample of up to 30 turns for the M3 review | Backlog | CLO-844 |
| CLO-852 | Give a new worktree's first prompt a hint from the project listing | Backlog | CLO-849 |
| CLO-853 | Make jevroute eval reproduce the probe's decision on every prompt | Backlog | CLO-837, CLO-846, CLO-847, CLO-848, CLO-849 |
| CLO-854 | Add jevroute doctor to report readiness, the provider in use and a model alias | Backlog | CLO-845, CLO-846, CLO-852, CLO-864 |
| CLO-864 | Add jevroute provider to choose between TypeSafe and OpenRouter and save the choice | Backlog | CLO-844, CLO-845 |

---

## Phase M2: Acceptance

Gates G2b (97 or more of 105 right, 0 wrong, 0 needless), G3 (100 fresh prompts) and G4a-c, on one frozen build and one provider.

| Task | Title | Status | Dependencies |
|------|-------|--------|--------------|
| CLO-855 | Write and freeze the fresh 100-prompt acceptance set | Backlog | CLO-835, CLO-838 |
| CLO-856 | Pass the live replay on the 105 probe prompts with the frozen acceptance build | Backlog | CLO-844 to CLO-853, CLO-864 |
| CLO-857 | Build the external timing harness and pass the failure matrix on development fixtures | Backlog | CLO-844 to CLO-853, CLO-856 |
| CLO-858 | Run the fresh acceptance set once through the timing harness and report G3 and G4a | Backlog | CLO-853, CLO-855, CLO-856, CLO-857 |

---

## Phase M3: One-week trial

Keep if G4d holds, `error:roster` never occurs, and at most 1 judged hinted turn steered Claude wrong. Otherwise remove.

| Task | Title | Status | Dependencies |
|------|-------|--------|--------------|
| CLO-859 | Install the accepted jevroute build as a user-level hook for the one-week trial | Backlog | CLO-851, CLO-854, CLO-856, CLO-857, CLO-858 |
| CLO-860 | Decide whether to keep or remove jevroute after the one-week trial | Backlog | CLO-859 |

---

## Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| M0a: Groundwork | 5 | 3 | In Progress |
| M0b: Behaviour test | 5 | 0 | Not Started |
| M1: Binary | 12 | 0 | Not Started |
| M2: Acceptance | 4 | 0 | Not Started |
| M3: One-week trial | 2 | 0 | Not Started |
