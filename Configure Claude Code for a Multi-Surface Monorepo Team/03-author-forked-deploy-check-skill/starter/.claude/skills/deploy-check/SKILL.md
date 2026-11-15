---
# TODO: Write the YAML frontmatter for this skill. It must include:
#
#   name: deploy-check
#   description: (one line naming what the skill does)
#   context: fork                    ← runs in a forked sub-agent (the key piece)
#   argument-hint: "..."             ← QUOTE any value containing a colon. Unquoted
#                                      `argument-hint: <foo: bar>` parses as a NESTED
#                                      MAPPING and breaks frontmatter loading.
#   allowed-tools: a READ-ONLY allowlist (Read, Grep, Glob, granular Bash sub-commands
#                  like Bash(git status:*) and Bash(gh pr view:*) — no Edit, Write,
#                  NotebookEdit, or unrestricted Bash).
#
# A note on schema drift: the current Claude Code IDE LSP (2026-05) may not list
# `context` or `allowed-tools` in its skill-frontmatter completions. That's the LSP
# lagging the product spec, not a problem with your file — see Troubleshooting in
# the exercise instructions.
name: deploy-check
description: Run the read-only pre-deployment checklist (clean tree, migrations, CI) and return a pass/fail summary
context: fork
argument-hint: "<optional: target branch or PR number>"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git status:*)
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(gh pr view:*)
  - Bash(gh pr checks:*)
---

# /deploy-check

Runs the team's pre-deployment validation checklist against the current working tree and the branch you're about to ship. Read-only by design — this skill never modifies files, never pushes, never deploys. It returns a single structured summary so the calling session can decide whether to proceed.

## Why this is a skill (not a CLAUDE.md addition)

<!--
TODO: Write a 2-3 line decision rubric explaining why /deploy-check is a SKILL
      rather than always-loaded CLAUDE.md guidance.

      The contrast you must convey:
        - Skill: on-demand, forked, task-specific. You only need it right before a
          deploy. It produces verbose intermediate output (file enumeration, diff
          parsing, check execution traces) that has no value once the summary is
          known.
        - CLAUDE.md: always-loaded, universal. Conventions that need to be present
          in every session (e.g. "tests are co-located", "throw ApiError for
          validation failures") belong here.

      Without this contrast, teammates default to dumping everything into CLAUDE.md
      and end up with a 600-line monolith that wastes context on every session.

      Rule-of-thumb summary at the end: on-demand / forked / task-specific → skill;
      always-loaded / universal → CLAUDE.md.
-->

A deploy check is needed only right before shipping, and it produces verbose intermediate output (file enumeration, diff parsing, check execution traces) that is worthless once the summary is known. That makes it a **skill**: on-demand, forked, and task-specific. 
Always-loaded guidance belongs in `CLAUDE.md` instead, for conventions every session needs, such as "tests are co-located" or "throw `ApiError` for validation failures". Putting everything in `CLAUDE.md` produces a 600-line monolith that wastes context on every session.

Rule of thumb: on-demand / forked / task-specific → skill; always-loaded / universal → `CLAUDE.md`.

## Why `context: fork`

<!--
TODO: Write the rationale paragraph for `context: fork`. It MUST do two things:

  (a) Explicitly state that the goal is to keep verbose intermediate output OUT OF
      THE MAIN SESSION / conversation. A deploy check walks the working tree,
      inspects diffs, and runs several enumeration passes — none of that has any
      value to the calling session once we know whether to ship. Only the
      structured summary should return to the main conversation.

  (b) Note that `context: fork` is a Claude Code PRODUCT FEATURE operating at the
      skill-invocation layer, conceptually analogous to the Architect's Playbook
      *Branching Reality* pattern (which describes session-level forking via
      `fork_session`). Mention both so a reader who knows the Playbook can map the
      mental model.
-->

The goal of `context: fork` is to keep verbose intermediate output **out of the main session and conversation**. A deploy check walks the working tree, inspects diffs, and runs several enumeration passes. None of that has any value to the calling session once we know whether to ship, so it all stays in the forked sub-agent and only the structured summary returns to the main conversation.

`context: fork` is a Claude Code **product feature** that operates at the skill-invocation layer. It is conceptually analogous to the Architect's Playbook *Branching Reality* pattern, which describes session-level forking via `fork_session`: both run work on a branch and bring back only what the caller needs.

## Checks

Run all three. Each check produces a pass-or-fail verdict; if any fails, the overall summary is **fail**.

<!--
TODO: Write at least THREE pre-deployment checks. For each check, declare:

  - Detect: the exact command(s) or signal(s) that determine whether the
            condition holds.
  - Pass:   what a passing result looks like.
  - Fail:   what a failing result looks like, including what to surface in the
            verdict-summary so the author can act on it.

Suggested checks (you may substitute equivalents if your team's deploy
shape needs different ones):

  1. Uncommitted changes — `git status --porcelain` returns empty.
  2. Migrations up-to-date with code — every new repository import in the diff
     since the target branch is backed by a migration file in the same branch.
  3. CI checks green on the open PR — `gh pr view --json statusCheckRollup`
     reports all required checks as SUCCESS.
-->

### 1. Uncommitted changes

- **Detect:** `git status --porcelain`.
- **Pass:** the output is empty (clean working tree, no untracked files).
- **Fail:** any output. Surface the count of modified and untracked files and the first few paths in `detail`, not the raw output.

### 2. Migrations up-to-date with code

- **Detect:** `git diff --name-only <target-branch>...HEAD` to list changed files, then `Grep` the changed files under `src/` for new imports from `src/db/` repository modules. For each repository the diff newly depends on, look for a matching `NNNN__short_description.sql` file added in the same diff.
- **Pass:** every new repository import is backed by a migration file added in the same branch, or no repository imports were added.
- **Fail:** a new repository import has no migration in the branch. Name the repository module and the missing migration in `detail`. Also fail on a migration filename that does not match `NNNN__short_description.sql`.

### 3. CI checks green on the open PR

- **Detect:** `gh pr view --json statusCheckRollup` (use `gh pr checks` if you need the per-check names).
- **Pass:** every required check reports `SUCCESS`.
- **Fail:** any required check is `FAILURE`, `PENDING`, or missing, or there is no open PR for the branch. Name the failing or pending checks in `detail`, not their logs.

## Output format

Return exactly this shape to the main session:

```
verdict: pass | fail
checks:
  - name: <check-name>
    status: pass | fail
    detail: <one line or empty>
```

Do not include the raw `git status`, raw diff hunks, or full check logs in the returned summary — those stay in the fork. If the author wants to investigate a failed check, they can re-invoke the skill targeting that single check or run the underlying command themselves.

## Personalization

<!--
TODO: Add a short note explaining that this skill is project-scoped
      (`.claude/skills/deploy-check/`) so the whole team gets the same checks.
      Mention that a teammate who wants a stricter personal variant — say, one
      that additionally fails when the diff exceeds 500 lines without a long
      enough PR description — can create a parallel skill at
      `~/.claude/skills/deploy-check-strict/` with a different name. Their
      variant will not be committed to the repo and will not affect teammates.
-->

This skill is project-scoped (`.claude/skills/deploy-check/`), so the whole team gets the same checks. A teammate who wants a stricter personal variant, for example one that also fails when the diff exceeds 500 lines without a long enough PR description, can create a parallel skill at `~/.claude/skills/deploy-check-strict/` with a different name. That variant is not committed to the repo and does not affect teammates.

## What this skill deliberately does not do

- It never pushes, deploys, or runs migrations. The `allowed-tools` allowlist is read-only by construction; even if a future maintainer adds `Write` here, the team's `/review` command should catch the change.
- It does not run the test suite. Tests have their own pre-merge gate in CI; duplicating that here would slow every deploy check without adding signal.
- It does not check for secrets in code. That's the job of the `gitleaks` pre-commit hook, which fails the commit, not the deploy.
