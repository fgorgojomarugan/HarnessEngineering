---
description: Conventions for co-located test files (*.test.ts / *.test.tsx)
paths:
  # TODO: add glob(s) that activate this rule for co-located test files anywhere in
  # the tree. Tests are co-located: Foo.tsx lives next to Foo.test.tsx — so the glob
  # needs to cross-cut both the components tree and the API tree.
  - "**/*.test.ts"
  - "**/*.test.tsx"
---

# Test file rules

<!--
TODO: Write at least one concrete, non-trivial convention for editing co-located
      test files (*.test.ts / *.test.tsx). Think about what should layer ON TOP of
      the React or API rules when the file under test sits in those directories.
      Examples: assertion-style enforcement, test-data-builder usage, forbidden
      patterns (snapshots, setTimeout, DB mocking).
-->

Loads when editing any `*.test.ts` or `*.test.tsx` file, alongside the React or API rules for the directory it lives in.

## Assertions

- Component tests query by role or label (`getByRole`, `getByLabelText`) and assert on user-visible output. Do not query by CSS class or `data-testid` unless no accessible query exists.
- API handler tests call the handler directly with a request object and assert on the returned `{ status, body }`. Never start the HTTP layer.

## Forbidden patterns

- No snapshot tests (`toMatchSnapshot`, `toMatchInlineSnapshot`). Assert on specific values instead.
- No `setTimeout` or real sleeps. Use fake timers or `await` the awaited condition (`findBy*`, `waitFor`).
- No mocking of the database layer. Repository tests run against the real PostgreSQL test instance.

## Structure

- One behavior per `it(...)`, with a name that states the expected outcome (`it("returns 404 when the order does not exist")`).
- Build test data with shared builders rather than inline object literals repeated across tests.
