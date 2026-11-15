# Plan mode vs. direct execution — team decision guide

Choosing between Claude Code's **plan mode** (investigate and propose before changing anything) and **direct execution** (change code immediately) is the single biggest leverage point in how the team uses the harness day-to-day. The wrong mode at either extreme costs us: plan mode for trivial fixes is friction; direct execution for architectural changes burns context and produces rework.

<!--
TODO: Add a blockquote citation for the Knight-Webb "SWE Is Becoming Plan and Review"
      anchor talk that frames this decision.

      IMPORTANT: source the citation from the Module 8 curriculum doc's anchor-talks
      table. Do NOT cite the Architect's Playbook — the Playbook contains zero
      plan-mode content and citing it would be a fabrication. The Knight-Webb talk
      lives in the curriculum doc, not the Playbook.
-->
> Anchor talk: Knight-Webb, "SWE Is Becoming Plan and Review."  

This doc walks four concrete decisions against our codebase: one plan-mode example, one direct-execution example, one Explore-subagent example, and one combined-workflow example.

---

## 1. Plan-mode example

<!--
TODO: Write a plan-mode worked example against this codebase. Requirements:

  - Touch AT LEAST THREE real files in src/. A natural candidate is extracting a
    shared `useCart(userId)` hook into src/hooks/ from three components that
    currently duplicate the pattern:
      - src/components/Cart/Cart.tsx
      - src/components/Checkout/Checkout.tsx
      - src/components/MiniCart/MiniCart.tsx
    (All three exist in this repo — confirm before referencing.)

  - State the reasoning that maps to Task 3.4: large-scale changes, multiple
    valid approaches, architectural decisions, multi-file modifications.

  - EXPLICITLY cite "prevent costly rework" (or equivalent phrasing) as the value
    of planning before committing. This is the Knight-Webb principle.

  - File-path rule: if you mention a file in backticks, it must actually exist
    in the repo. For hypothetical/future files (e.g. the extraction target that
    doesn't exist yet), use PROSE form (no backticks) instead. Otherwise the
    validator will flag a dangling reference.
-->

**Task:** extract a shared `useCart(userId)` hook from three components that each re-implement the same pattern: `src/components/Cart/Cart.tsx`, `src/components/Checkout/Checkout.tsx`, and `src/components/MiniCart/MiniCart.tsx`. All three hold `items` in `useState`, load them with `fetchCart(userId)` inside `useEffect`, and derive `total` with the same `useMemo` reduce.

**Why plan mode:** this is a large-scale, multi-file change with several valid approaches and an architectural decision at its center.

- The hook could return only `{ items, total }`, or also `loading`, `setQuantity`, and `itemCount`. `Cart` needs the mutation and cancellation handling, while `MiniCart` needs almost nothing. One shape has to serve all three.
- `Cart` guards against a stale response with an `active` flag. `Checkout` and `MiniCart` do not. The hook has to pick one behavior, which changes what two of the components do today.
- The new hook file does not exist yet. It goes in the hooks directory, and where it lives and how it is named is part of the decision.
- Three components change at once, plus the existing `src/components/Cart/Cart.test.tsx`.

**The value of planning is that it prevents costly rework.** This is the Knight-Webb principle: invest in the plan and the review before committing to edits. If we direct-executed and the chosen API turned out too heavy for `MiniCart`, we would rewrite the hook and all three call sites a second time and bury the intent in the change history. In plan mode, Claude reads the three components, proposes one hook shape with its trade-offs, and the team approves or redirects before a single file is touched.

---

## 2. Direct-execution example

<!--
TODO: Write a direct-execution worked example. Requirements:

  - Target a single, well-scoped change in ONE function. A natural candidate is
    adding a `min: 0` validation to the quantity field in the orders schema or
    handler:
      - src/api/orders/handler.ts (or src/api/_schemas/orders.ts)
    Confirm the file exists before referencing it.

  - State the reasoning that maps to Task 3.4: simple, well-scoped changes.

  - Convey the bar for "direct execution": you (the author) already know what
    the diff looks like before invoking Claude. If you can describe the change
    in one sentence and predict the patch, skip planning.
-->

**Task:** cap the quantity of a single order line at 100. The only change is in `orderCreateSchema` in `src/api/_schemas/orders.ts`, where the quantity field is currently `z.number().int().min(1)`:

```diff
-        quantity: z.number().int().min(1),
+        quantity: z.number().int().min(1).max(100),
```

(The originally suggested `min: 0` check is already covered here by `.min(1)`, and `src/api/orders/handler.ts` parses the body with this schema, so the handler itself does not change.)

**Why direct execution:** this is a simple, well-scoped change in one place, and it needs no investigation. The schema is the single boundary where request bodies are validated, per the API standards, so nothing downstream re-validates it.

**The bar for direct execution is that you already know what the diff looks like before invoking Claude.** If you can describe the change in one sentence ("cap order-line quantity at 100 in the orders schema") and predict the patch, skip planning. Plan mode here would be friction: it costs a round trip to confirm a one-line change you could already write.

---

## 3. Explore-subagent example

<!--
TODO: Write an Explore-subagent worked example. Requirements:

  - A real discovery task in this codebase. A natural candidate: "find every
    place we call `processRefund`" — the answer touches src/api/orders/refund.ts,
    src/api/billing/issue.ts, and src/services/payment.ts. Confirm the files
    and the call sites exist before referencing them.

  - State the reasoning that maps to Task 3.4: isolating verbose discovery output
    and returning summaries to preserve main conversation context.

  - REFERENCE THE SCRATCHPAD PATTERN (Architect's Playbook). The Explore sub-agent
    should write its working notes to a scratchpad file (e.g. tmp/refund-callsites.md)
    so the inventory survives the main session's context window. Name it
    explicitly — "scratchpad pattern" should appear in your text.
-->

**Task:** before changing the refund flow, find every place the codebase calls `processRefund`. A search of `src/` shows the function is defined in `src/services/payment.ts` and called from two handlers: `src/api/orders/refund.ts` and `src/api/billing/issue.ts`.

**Why an Explore subagent:** this is pure discovery. Answering it means grepping, opening several files, and reading surrounding code to see how each call site builds its input. That verbose intermediate output is useless once we know the answer, so we isolate it in the subagent and return only a summary. The main conversation keeps its context for the actual change.

**The scratchpad pattern (Architect's Playbook):** ask the Explore subagent to write its working notes to a scratchpad file, such as a refund call-sites file in a tmp directory, listing each call site with its file, line, and the arguments it passes. The inventory then survives the main session's context window. If the session is compacted or restarted, the next step reads the scratchpad file instead of repeating the search.

What returns to the main session is a short summary: one definition, two call sites, and the path to the scratchpad file.

---

## 4. Combined workflow — plan mode for investigation, then direct execution

<!--
TODO: Write a combined-workflow worked example. This is the most subtle of the
      four — developers often see plan mode and direct execution as binary. The
      combined workflow uses plan mode for the DISCOVERY part (where you don't
      yet know the call-site list) and direct execution for the MECHANICAL part
      (where the rename is keystrokes once the list is known).

      Requirements:

      - A real change in this codebase where investigation should precede edits.
        A natural anchor: renaming `ordersRepo.findById` → `ordersRepo.getById`
        in src/db/orders.ts to align with a team naming convention
        (get* for single-row reads, find* for multi-row). The investigation
        question is "where is findById called, and are any of them dynamic
        (constructed string lookups grep would miss)?" — plan mode handles that.
        Once the call-site list is in hand, the rename itself is mechanical:
        direct execution.

      - State the reasoning that maps to Task 3.4: "Combining plan mode for
        investigation with direct execution for implementation."

      - Show the flow as a 3-step sequence: (1) plan mode investigates and
        proposes; (2) you approve the plan; (3) direct execution applies the
        rename and runs tests.
-->

**Task:** rename `ordersRepo.findById` to `ordersRepo.getById` in `src/db/orders.ts`, to follow the team naming convention (`get*` for single-row reads, `find*` for multi-row reads).

**Why combine the two modes:** developers often treat plan mode and direct execution as a binary choice. The combined workflow uses **plan mode for investigation, then direct execution for implementation**. The rename itself is mechanical, but we do not yet know the full call-site list, and a missed caller breaks at runtime. The investigation question is "where is `findById` called, and are any of the calls dynamic (a constructed string lookup that grep would miss)?" Plan mode answers that. Once the list is in hand, the rename is keystrokes.

**The flow:**

1. **Plan mode investigates and proposes.** Claude searches for every use of `findById`. Today it finds the definition in `src/db/orders.ts` and two callers, `src/api/orders/refund.ts` and `src/api/billing/issue.ts`. It also checks for dynamic access such as `ordersRepo[name]`, and any tests or mocks that reference the old name. It proposes the exact edit list and writes nothing.
2. **You approve the plan.** You confirm the call-site list is complete and that no dynamic lookup was missed. If one was, you fix the plan now, before any file changes.
3. **Direct execution applies the rename and runs tests.** With the plan approved, Claude edits the definition and each caller in one pass, then runs the test suite to confirm nothing still references the old name.

Planning alone would add a round trip to a mechanical edit, and direct execution alone would risk a missed caller. Combining them puts the thinking where it is needed and the typing where it is cheap.

---

## Quick reference

| Situation | Mode |
|-----------|------|
| Single function, fix is obvious, you can predict the diff | Direct execution |
| Multi-file refactor, API shape is debatable | Plan mode |
| Discovery / inventory across the codebase, you'll throw away the intermediate steps | Explore subagent |
| Investigation-then-mechanical-change | Plan mode → direct execution |
| Architectural decision (which database, which queue) | Plan mode, possibly with a fork to compare options |

When in doubt: plan mode is recoverable (you can switch to execution), but direct execution on a complex change is not. Default to plan when uncertain.
