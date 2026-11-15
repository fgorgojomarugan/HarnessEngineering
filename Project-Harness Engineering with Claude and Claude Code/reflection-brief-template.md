# Reflection Brief — Harness Engineering Capstone

**Name:** : Fernando Gorgojo Marugan
**Date:** : 16 - nov - 2026

Replace each `→` with your answer. **Every answer cites at least one artifact from your own runs** — a run ID, file path, token count, claim outcome, or test count. Uncited answers do not pass. 3–6 sentences each unless noted. Paste short artifact snippets where they help.

**Environment**

- Model(s): claude-sonnet-5-5 (agent loop), claude-haiku-5-5 (classification)
- OS / Python: windows / 3.12.10
- Approx. API spend: 4.50$

---

## Part 1 — Per-system

### System 1 — Agentic loop

1. **Loop control.** Quote the `stop_reason` sequence from one trace. Name the file and function that decides continue-vs-stop, and how.
   - In run `20261115_171946`, `traces/claim_04_neighbor_injury.jsonl` shows `tool_use → tool_use → tool_use → tool_use → end_turn` (turns 1–5: `lookup_policy`, 5× `record_claim_fact`, `classify_claim`+`assess_severity`, `route_to_adjuster`, final confirmation).  
   - The decision lives in `claims_intake/loop.py`, function `run()`: the `while True` body returns a `FinalState` when `response.stop_reason == "end_turn"`, executes the tools and continues when it is `"tool_use"`, and otherwise raises `UnexpectedStopReason`. There is no turn counter in the condition; the only safety net is `budget.check()`, which raises `BudgetExceeded` instead of silently truncating.

2. **Anti-pattern.** Name one anti-pattern `test_antipatterns.py` checks for. What would break in your run if the loop used it?
   - `tests/test_antipatterns.py::test_no_integer_literal_iteration_cap_in_loop` fails if `loop.py` uses `for _ in range(<int>)` or `while turn < <int>` as the stopping mechanism. In my run the claims need between 2 and 5 turns (claim_04 and claim_08 need 5, per `summary.md`). 
   - A fixed cap of e.g. 3 would cut those two off before `route_to_adjuster` (turn 4) and their final `end_turn` (turn 5), leaving queued work unrecorded. Sibling checks (`test_no_string_membership_against_text_in_loop`) guard against parsing assistant text for "done" instead of reading `stop_reason`.

3. **Tool design.** Pick two tools with overlapping inputs. How do the descriptions prevent misrouting? What did a structured tool error let the agent do that a generic string would not?
   -  `route_to_adjuster` and `escalate_to_human` overlap (both terminal, both take a summary and the claim facts) and `classify_claim` overlaps with both on `claim_type`.  
   - The descriptions in `claims_intake/tools.py` split them by explicit thresholds: route is for "classification confidence at least 0.6 and severity assessed", escalate is for "below 0.6 even after clarification" or unsafe-to-route cases, and classify says "if confidence is below 0.6, prefer escalate_to_human". 

4. **Your numbers.** Quote the turn count and cost for one claim. How does it differ from the README sample, and why?
   - Claim `claim_04_neighbor_injury` (run `20261115_171946`): 5 turns, 17,436 input / 876 output tokens, est. cost $0.0218 (11.8 s), routed to `liability`/high. The whole run cost $0.1102 across 8 claims. The README for exercise 3 expects "7 routed, 1 escalated" at ≈ $0.05, but mine gave 3 routed and 5 escalated, and the total is about double. 5 of the 8 escalations in `escalations.jsonl` have `reason: "model ended its turn without a terminal action (deterministic backstop)"` (claims 01, 02, 03, 06, 07), meaning the model stopped with `end_turn` on turn 2–3 without calling `route_to_adjuster`/`escalate_to_human`, and `run.py::_escalate_without_terminal` caught it.  
    The cost is higher because every turn resends the growing history (input is ~2.8k tokens on turn 1 and ~4.2k on turn 5, so input tokens accumulate quadratically-ish per claim) on top of ~2.7k tokens of system prompt and tool schemas. The earlier run `20261026_205214` was $0.1211, so the gap with the README is consistent, not a one-off.

### System 2 — Context strategy

5. **The reduction.** From `budget.json`: baseline tokens, assembled tokens, reduction %. Which section dominates the assembled context, and why keep it verbatim?
   - `04-assemble-and-locate/solution/runs/20261115-181722/budget.json` reports `baseline_tokens` 38,708, `assembled_tokens` 16,814 and `reduction_pct` 56.56 (counted with the `messages.count_tokens` endpoint). The `active` section dominates with 15,789 of 16,814 tokens (~94%), against 204 for `case_facts`, 388 for `resolved_refund` and 451 for `resolved_subscription`. The active payment-method update is still being worked, so its exact tool outputs (gateway attempt, `AVS_MISMATCH`, card last-4 7782) are what the next turn depends on. Summarizing it would risk losing the very details the agent has to act on, so it stays verbatim. The earlier run `20261115-181500` gives the same 38,708 → 16,813 (56.56%).

6. **Summarize vs preserve.** State the rule for what gets summarized vs kept byte-exact, citing your per-section token numbers.
   - Rule: resolved issues are summarized, because only their outcome matters now, while anything still active or exact-valued is kept byte-exact (the `active` section verbatim, plus identifiers, amounts and status tokens in the `case_facts` block). In `budget.json` (run `20261115-181722`) the refund thread was compressed from 12,344 input tokens to 388 (`compression_api.refund` output 375) and the subscription thread from 11,485 to 451 (output 438), roughly a 30x reduction each. `active` stays at 15,789 tokens and `case_facts` costs only 204 tokens for values like `refund_amount_usd: $22.14` and `payment_update_failure_code: AVS_MISMATCH`. The summaries lose prose, not the values anyone will be asked for.

7. **Facts block.** Compare `eval.jsonl` to `eval_control.jsonl`. Which question regressed, and what does that prove?
   - Both runs (`20261115-181500` and `20261115-181722`) pass 6/6 in `eval.jsonl`. `eval_control.jsonl` (same context without the case-facts block) passes Q1 (refund 22.14) but fails Q6, "the exact status token for the payment-method update" (expected `in_progress`). The control answer is: "I don't have access to a structured case record or status token for the payment-method update issue." Q1 survives because the amount also appears in the resolved-refund summary and the conversation text. The `in_progress` status only exists as a structured token in the case-facts block, so the regression shows that block is what carries exact values the prose and summaries don't preserve. It is also reproducible, since the same Q6 failure appears in both runs.

### System 3 — Claude Code config

8. **Path-scoped rules.** Quote the glob frontmatter from one rule file. Why is it better than a directory-level CLAUDE.md for cross-cutting conventions?
   - `.claude/rules/api.md` (in `04-plan-mode-and-explore-decision-doc/solution`) starts with `paths:` → `- "src/api/**/*"`, and `.claude/rules/tests.md` uses `- "**/*.test.tsx"` and `- "**/*.test.ts"`. These rules load only when Claude edits a matching file. A directory-level CLAUDE.md can't express a convention that cuts across directories: co-located test files sit next to both React and API code, so you'd have to duplicate the test rules in every folder. The glob in `tests.md` applies once everywhere, and layers on top of the React or API rule for the same file. Our own `CLAUDE.md` states this preference under "Directory-level".

9. **Forked skill.** Quote the `context: fork` and `allowed-tools` lines. What does running forked + read-only buy you? What breaks without it?
   - `.claude/skills/deploy-check/SKILL.md` has `context: fork` and an `allowed-tools` list containing only `Read`, `Grep`, `Glob` and read-only commands such as `Bash(git status:*)`, `Bash(git diff:*)`, `Bash(gh pr checks:*)`. The fork keeps the verbose discovery output (file lists, diffs, check traces) out of the main session, so only the `verdict: pass | fail` summary comes back. The read-only allowlist makes it safe by construction: the skill cannot write, push or deploy. Without the fork, the main context fills with output that has no value once the verdict is known. Without the allowlist, a pre-deploy check could change the tree it is validating, and the validator checks this with `write_capable_tools` (`tests/test_us04_deploy_check_skill.py`, 35 tests passing in my run).

10. **Scope.** From the validator output: project-level vs user-level scope. Give one example of each from this config.
   - The validator (`ecommerce-team-config .`) printed `OK` and `pytest -q` gave 35 passed. It checks `CLAUDE.md` through `distinguishes_project_vs_user_scope`, and the scope table there is: project-level means `./CLAUDE.md`, `.claude/standards/` and `.claude/rules/`, which live in git and are shared with the team. User-level means `~/.claude/CLAUDE.md`, `~/.claude/commands/` and `~/.claude/skills/`, which stay on your laptop. Project example: `.claude/skills/deploy-check/SKILL.md`, which everyone gets. User example from this config: a personal `/morning` summary command or a stricter `~/.claude/skills/deploy-check-strict/`, which would not reach teammates. If a convention is ignored, `/memory` shows which files actually loaded.

### System 4 — Orchestration

11. **Push work down.** Defects the SQL query returned vs warm-tier total. Name the indexed query. Why does the model never see the full history?
   - My recorded run (`04-fork-scratchpad/starter/data/shift_scratchpad.jsonl`, evidence `"0 new defects analyzed since 2026-04-29T22:00:00Z"`) returned 0 defects out of the 40 rows in `data/warm.sqlite`, because the newest defect is `2026-04-29T12:05:28Z`. Running the same query by hand on that DB, a `since` of 2026-04-28 returns 1 row and 2026-04-20 returns 5. The query is `WarmStore.defects_since` in `shift_monitor/warm.py`: `SELECT * FROM defects WHERE ts > ? ORDER BY ts DESC LIMIT ?` (limit 50, called from `pipeline.run_shift`), and `EXPLAIN QUERY PLAN` reports `SEARCH defects USING INDEX idx_defects_ts (ts>?)`. SQLite filters and caps the rows, so `build_rich_prompt` receives only a bounded slice. The model never sees the full history, so the prompt size stays flat however much the warm tier grows.

12. **Crash recovery.** The resume-vs-fresh decision and its staleness threshold (`recovery.py`). Why is a fresh start with an injected summary sometimes more reliable than resuming?
   - `decide()` in `shift_monitor/recovery.py` returns `"fresh"` if the manifest has no steps or is `complete`, and `"resume"` only if the last step's `ts` is within `STALE_RESUME_THRESHOLD_MINUTES = 30` of now (about 1/16 of an 8-hour shift). Anything older is `"fresh"`. I only exercised this through the tests (the `manifest_S1..S4.jsonl` fixtures under `.pytest_tmp`), not through a real crash in my runs. A fresh start with an injected summary of the findings already in the manifest is more reliable when the partial is stale. New defects may have arrived since the crash, and resuming would carry half-finished assumptions that no longer match the data. A summary of verified findings is a small, known-good input.

13. **Small state.** Byte size of your `hot_state.json`. Why does the budget matter for a system run once per shift, indefinitely?
   - `04-fork-scratchpad/starter/data/hot_state.json` is 658 bytes (the same in `02-invocation-pipeline/starter/data/`), against `HOT_STATE_BYTE_BUDGET = 5_120` in `shift_monitor/state.py`, so about 13% of the budget. `write_atomic` raises if the payload exceeds the budget, and `pipeline._trim_to_budget` trims before writing. A job that runs once per shift indefinitely would otherwise grow the state a little each run until it dominates every prompt and eventually fails. The hard cap forces the hot state to hold only the current summary, alerts and thresholds, and pushes everything else to the warm SQLite tier.

---

## Part 2 — Synthesis

*Graded on connecting two or more systems. Cite a named file/artifact from each.*

14. **Three layers.** Point to a file/artifact for each layer and justify.
   - Model: the Claude call that decides each step; in the claims run `20261115_171946`, `traces/claim_04_neighbor_injury.jsonl` shows it choosing `lookup_policy → record_claim_fact → classify_claim → route_to_adjuster` on its own.
   - Harness: `claims_intake/loop.py` and `tools.py`, plus `.claude/` config in System 3. The harness decides what the model can do and when to stop (`stop_reason` dispatch, tool schemas, `Budget`), and the model never decides those.
   - Orchestration: `shift_monitor/pipeline.py`, `recovery.py` and `state.py` (System 4). They run one fresh session per shift, restore small state from `hot_state.json` (658 bytes) and recover from crashes. Each layer wraps the one below it.

15. **Deterministic vs prompt.** Cite one behavior guaranteed in code (terminal tool, read-only allowlist, atomic write, byte budget) and one guided by prompt. When is each right?
   - In code: the backstop in `claims_intake/run.py::_escalate_without_terminal`, which escalated 5 of 8 claims in run `20261115_171946` when the model ended without a terminal tool. Also the 5,120-byte hot-state cap in `state.py`. By prompt: the "confidence below 0.6, prefer escalate_to_human" guidance in the `tools.py` descriptions. Use code for rules that must never fail (safety, cost, data integrity), because a model can ignore a prompt, as those 5 claims showed. Use prompts for judgment calls like classification and severity, where rigid code can't cover the cases.

16. **Context, two faces.** Compare context management in System 2 (intra-session) and System 4 (cross-session) with cited numbers from both. Same principle, different mechanism — how?
   - System 2 (within a session): `budget.json` in run `20261115-181722` cut 38,708 tokens to 16,814 (56.56%) by summarizing resolved threads and keeping the active one verbatim. System 4 (across sessions): each shift starts from `hot_state.json` at 658 bytes (cap 5,120) plus a bounded `defects_since` query (`LIMIT 50`), instead of replaying history. The principle is the same: give the model only what the next decision needs and keep exact values safe elsewhere. The mechanism differs: System 2 compresses a transcript and pins `case_facts`, while System 4 stores state in tiers (hot, warm SQLite, cold) and loads a small slice each run.

17. **Reliability you can't see in one run.** Name one behavior a test guarantees that a single successful run would not reveal. Why does it matter before shipping?
   - `tests/test_antipatterns.py` (claims) checks by AST that `loop.py` has no integer iteration cap and branches on `stop_reason`, and the crash-recovery tests in System 4 check that a stale manifest (older than 30 minutes) gives `fresh`. A single successful run, like claim_04's 5 turns, would pass either way and would not reveal a hidden hard-coded cap or a broken recovery path. These failures show up only on the rare long claim or the real crash, so it matters to catch them before shipping.

18. **Blast radius.** Pick one system. What's the blast radius if it misbehaves, and what's the kill switch? Ground it in that system's tools, enforcement points, and state.
   - System 1 (claims intake). If it misbehaves, it can misroute a claim or escalate it unnecessarily. In run `20261115_171946` that happened to 5 of 8 claims, but the damage stayed small: the tools only append to `queues/*.jsonl` and `escalations.jsonl` in that run's folder, and a human reviews escalations. Enforcement points are the schema-validated tools in `tools.py` (e.g. `route_to_adjuster` refuses before `classify_claim`) and the one-terminal-tool-per-claim rule. The kill switch is `Budget` in `budget.py`: `max_input_tokens` and `max_wall_clock_s` raise `BudgetExceeded`, which `run.py` catches so the claim stops instead of looping. State is per-session, so nothing carries over to the next claim.

---

## Part 3 — Honest assessment

19. **What broke.** One thing that failed first try in your environment, and how you fixed it. (If nothing, what you checked to be sure.)
   - On Windows, the default pytest temp path (`PATH_TEMP`) pointed to a location without write permissions, which made the tests fail. I fixed it by adding `addopts = "--basetemp=.pytest_tmp"` to the `pyproject.toml` config files (e.g. `./solution/pyproject.toml`), which changes the base temp directory used by the `tmp_path` fixture to a folder inside the project.

20. **What you'd change.** One architectural decision you'd make differently, grounded in what you observed.
   - I would make the claims agent's terminal step code-enforced instead of prompt-guided. In run `20261115_171946`, 5 of 8 claims ended with `end_turn` without calling `route_to_adjuster` or `escalate_to_human`, and only the backstop in `run.py` caught them. Setting `tool_choice` to force a terminal tool once classification and severity are recorded, or sharpening the system prompt, would route more claims correctly and cut the extra cost.
   - I would also have liked to go deeper into the Level 3 fork executions (`shift_monitor/fork.py`: `fork_for_hypothesis` and `merge_findings`) to avoid manual steps. In my System 4 runs I had to create and compare the fork folders by hand (e.g. `data/forks_root/Hipotesis Inicial` and `Hipotesis Final`), when a script could fork, run and merge the hypotheses automatically.
