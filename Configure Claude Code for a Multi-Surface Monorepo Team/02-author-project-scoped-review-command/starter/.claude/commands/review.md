---
# TODO: Write the YAML frontmatter for this command. It must include:
#
#   description:   one line, ≥10 characters, naming what the command does
#   argument-hint: short description of how to pass a target (PR ref, diff range, or file path)
#   allowed-tools: a list of READ-ORIENTED tools only — no Edit, Write, NotebookEdit, or
#                  unrestricted Bash.
#
# Granular Bash sub-command allowlisting is the canonical pattern. For example:
#   - Bash(git diff:*)
#   - Bash(git log:*)
#   - Bash(gh pr view:*)
# This lets you allow READ operations on git without unlocking the full shell. The
# command should be able to run `git diff`, `git log`, `gh pr view`, `gh pr checks`,
# etc. — but NOT `git push`, `git commit`, or arbitrary `Bash(...)`..
description: Review a pull request or diff against the team's conventions (read-only)
argument-hint: "<pr-number | pr-url | branch | git diff range | file path>"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git show:*)
  - Bash(git status:*)
  - Bash(gh pr view:*)
  - Bash(gh pr diff:*)
  - Bash(gh pr checks:*)
---

# /review — team PR review

You are reviewing the diff identified by `$ARGUMENTS` against this repository's conventions. Apply the path-scoped rules in `.claude/rules/` (they auto-load based on the files touched) and the shared standards in `.claude/standards/`.

## Phase 1 — Interview pattern

<!--
TODO: Write the interview-pattern subsection. The reviewer agent should ask clarifying
      questions BEFORE reporting findings whenever the author's intent is ambiguous.

      Why this matters (and why it's not obvious on first read): without an interview
      step, the reviewer commits to a confidently-wrong verdict on ambiguous changes —
      e.g. a refactor that touched no test files. The author then has to argue against
      a "no test coverage" finding when the behavior was already covered upstream. The
      interview pattern asks first.

      Name at least three concrete trigger conditions where the reviewer should
      interview rather than report. Suggested triggers:
        - dependency changes (package.json or pyproject.toml diffs)
        - public API response shape changes or DB column changes
        - refactors with no corresponding test changes
        - changes that touch multiple surfaces (API + components + DB) at once
-->

Before reporting any finding, read the diff and decide whether the author's intent is clear. If it is ambiguous, **stop and ask the author clarifying questions first**. Do not report a verdict until they answer. A confident verdict on a misread change forces the author to argue against a false finding (for example, "no test coverage" on a refactor whose behavior is already covered upstream).

Interview instead of reporting when any of these triggers applies:

- **Dependency changes:** `package.json`, `pyproject.toml`, or lockfile diffs. Ask why the dependency is needed and whether an existing one already covers it.
- **Public API response shape or DB column changes:** a field is added, removed, renamed, or retyped, or a column or migration changes. Ask who consumes it, whether the change is backward compatible, and how existing data is migrated.
- **Refactors with no test changes:** source files change but no `*.test.ts(x)` file does. Ask which existing tests cover the behavior before flagging missing coverage.
- **Multi-surface changes:** the diff touches API, components, and DB together. Ask whether it ships as one change and in what order the pieces deploy.

Keep the interview short: at most three specific questions, each tied to a file or hunk in the diff. If none of the triggers applies and the intent is clear, skip this phase and go straight to Phase 2.


## Phase 2 — Review criteria

<!--
TODO: Write the explicit must-report vs. skip taxonomy. The point of explicit criteria
      (vs vague "be thorough" instructions) is that two teammates running this command
      on the same PR should reach the same verdict.

      Must report: at minimum, name categories for bugs (logic errors, missing await,
      race conditions, off-by-one), security (raw SQL with user input, missing auth,
      secrets in code, dangerouslySetInnerHTML), convention violations the path-scoped
      rules catch, breaking changes, and migration safety.

      Skip: at minimum, name categories the reviewer should NOT block on — minor
      formatting (Prettier handles it), naming bikeshed when the name is fine, personal
      stylistic preferences not encoded in rules/standards, and TODOs that already have
      tracked tickets.

      The skip list is what keeps false positives from destroying author trust.
-->

Apply these criteria literally. Two teammates running this command on the same PR should reach the same verdict.

### Must report

- **Bugs (`bug`):** logic errors, missing `await` on async calls, race conditions, off-by-one errors, unhandled promise rejections, and writes spread across several `await pool.query` calls with no wrapping transaction.
- **Security (`security`):** raw SQL built from user input, missing authentication or authorization checks on a handler, secrets or credentials in code, and `dangerouslySetInnerHTML`.
- **Convention violations (`convention`):** anything the path-scoped rules in `.claude/rules/` or the standards in `.claude/standards/` forbid. Examples: `throw new Error(...)` in a handler, handlers that write to the response object, handlers that bypass the repository layer, class components, snapshot tests, and DB mocking in tests.
- **Breaking changes (`breaking`):** removed or renamed response fields, changed status codes, retyped fields, or a changed handler or repository signature with callers not updated in the same diff.
- **Migration safety (`breaking`):** a destructive migration (`DROP`, `TRUNCATE`, a column rename, or a `NOT NULL` column without a default on an existing table), a migration that edits an earlier one, a filename that breaks the `NNNN__short_description.sql` pattern, or a "rollback" written as anything other than a new forward migration.

### Skip (never block on these)

- **Minor formatting:** whitespace, quotes, trailing commas, and import order. Prettier handles it.
- **Naming bikeshed:** the name is accurate and follows the conventions, even if you would pick another.
- **Personal stylistic preferences** not encoded in the rules or standards.
- **TODO comments that reference a tracked ticket** (for example `TODO(SHOP-123)`). An untracked TODO that hides a bug is still a `bug`.
- **Code the diff does not touch,** unless the diff makes it newly wrong.

If you are unsure whether something is a must-report, check the rules and standards. If they do not forbid it, skip it.


## Phase 3 — Bundling: interacting vs. independent findings

<!--
TODO: Write the bundling guidance. The contrast is hard to internalize without a
      concrete pair of examples (which you'll write in the Examples section below).

      Interacting findings: those that overlap or affect the same fix. Bundle into
      ONE detailed message with all context. Example: a missing `await` and a missing
      transaction wrapper on the same function — the author needs to see them together
      because the fix changes both lines.

      Independent findings: separate functions, separate files, no shared fix. Report
      SEQUENTIALLY as discrete items so each piece of feedback is actionable.

      Give a one-line heuristic for telling them apart (e.g. "if fixing A changes the
      code B references, they are interacting").
-->

Group findings by whether their fixes touch the same code.

- **Interacting findings** overlap or share one fix. Bundle them into **one** detailed finding that lists every issue and its context together, because the author has to change all of it at once. Example: a missing `await` and a missing transaction wrapper in the same function. Fixing one changes the lines the other points at, so reporting them separately would give contradictory advice.
- **Independent findings** live in separate functions or files and share no fix. Report them **sequentially** as discrete items, so the author can act on and verify each one on its own. Do not merge them into one long message.

Heuristic: **if fixing A changes the code that B references, they are interacting; otherwise they are independent.**

When bundling, use the severity of the most serious issue in the bundle, and name every affected line in the `fix:` recommendation.

## Phase 4 — Output format

For each finding, produce:

```
[severity] path/to/file.ts:line
finding: <one-sentence description>
fix: <one-sentence recommendation>
```

Severity is `bug` | `security` | `convention` | `breaking`. End with a one-line verdict: `approve`, `comment`, or `request-changes`.

## Examples

<!--
TODO: Write at least TWO concrete input/output examples using the format above.

Per Task 3.5, examples are the difference between a command that produces
consistent output across team members and one that produces wildly varying output.

Example 1 — INDEPENDENT findings. Show a diff with two unrelated convention
violations on the same file (e.g. a handler returning a `{ status: 404 }` shape
instead of throwing ApiError, AND a raw SQL call that bypasses the repository
layer). Report each as a separate `[convention]` finding. End with a verdict.

Example 2 — INTERACTING findings. Show a diff where multiple problems share a
single fix (e.g. a refundOrder handler that has missing awaits AND no transaction
wrapper AND wrong ordering between paymentService and DB writes). Bundle them
into ONE `[bug]` finding that lists the three issues together because the fix
changes the same three lines. End with a verdict.
-->

### Example 1 — Independent findings

Input diff (`src/api/orders/getOrder.ts`):

```diff
 export async function getOrder(req: ParsedRequest) {
+  const order = await pool.query("SELECT * FROM orders WHERE id = $1", [req.params.id]);
+  if (!order.rows[0]) {
+    return { status: 404, body: { error: "not found" } };
+  }
+  return { status: 200, body: order.rows[0] };
 }
```

Output:

```
[convention] src/api/orders/getOrder.ts:2
finding: The handler queries the connection pool with raw SQL instead of calling a repository function from src/db/.
fix: Add or reuse a `findOrderById` function in the orders repository and call it from the handler.

[convention] src/api/orders/getOrder.ts:4
finding: The handler returns `{ status: 404, ... }` for a not-found case instead of throwing `ApiError`.
fix: Replace the return with `throw new ApiError(404, "ORDER_NOT_FOUND", "Order not found")`.

verdict: request-changes
```

The two findings are independent: replacing the SQL does not change the not-found branch, so each is reported on its own.

### Example 2 — Interacting findings

Input diff (`src/api/orders/refundOrder.ts`):

```diff
 export async function refundOrder(req: ParsedRequest) {
+  const order = orderRepo.findById(req.params.id);
+  orderRepo.markRefunded(order.id);
+  paymentService.refund(order.paymentId, order.total);
+  return { status: 200, body: { refunded: true } };
 }
```

Output:

```
[bug] src/api/orders/refundOrder.ts:2-4
finding: Three problems share one fix: `findById`, `markRefunded`, and `refund` are all called without `await`, so `order` is a Promise and the handler returns before any work finishes; the DB write and the payment call are not wrapped in a transaction; and the order is marked refunded before the payment succeeds, so a failed refund leaves the order refunded with no money returned.
fix: Wrap the work in `withTransaction`, `await` every call, and call `paymentService.refund` first, then `markRefunded`, so a payment failure rolls back with no state change.

verdict: request-changes
```

The findings are bundled because adding `await`, the transaction, and the reordering all rewrite the same three lines.

## Notes

- This command is project-scoped (`.claude/commands/review.md`) so everyone on the team gets the same review. If you want to layer personal preferences (e.g. a stricter accessibility check on your own PRs), put a `~/.claude/commands/review-strict.md` in your home directory — it will not affect teammates.
- If a finding requires running code or modifying files to verify, ask the author to run a specific check rather than attempting it from the review session. This command's `allowed-tools` are read-only by design.
