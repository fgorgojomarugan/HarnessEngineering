---
description: Conventions for Node.js API handlers under src/api/
paths:
  # TODO: add glob(s) that activate this rule when Claude edits files under src/api/
  #- "TODO/**/*"
  - "src/api/**/*"
---

# API handler rules

<!--
TODO: Write at least one concrete, non-trivial convention for editing files under
      src/api/. Pull from `.claude/standards/api.md` (already complete) for context,
      but write something more specific than the standard — a rule that ONLY fires
      when editing API handler files. For example: handler signature shape, error-type
      enforcement, or repository-import boundaries.
-->

Loads when editing any file under `src/api/`.

## Handler signature

- Handlers are `async` functions with the signature `async function handler(req: ParsedRequest): Promise<{ status: number; body: unknown }>`. Never accept or touch the raw `res` object.

## Errors

- Expected failures are raised with `throw new ApiError(status, code, message)`. A bare `throw new Error(...)` in a handler is a bug: it surfaces as an opaque 500.

## Repository boundary

- Handlers import from `src/db/` repository modules only. Never import `pg`, the connection pool, or write raw SQL in `src/api/`.
- Multi-statement writes go through `withTransaction` in the repository layer, not composed in the handler.

## Schemas

- Parse the request body with the matching `zod` schema from `src/api/_schemas/` as the first step of the handler. When a response gains a field, update `src/api/_schemas/responses/` in the same change.



