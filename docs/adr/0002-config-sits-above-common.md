# 2. `config` sits one layer above `common`

Date: 2026-05-29

## Status

Accepted

## Context

`docs/RANGE_DESIGN_V1.md` §6 says "common and config depend on nothing internal."
Read literally that would forbid `config → common`, but `config` legitimately
needs `common` (errors, shared types) once those exist (Step 0.2). The import
boundaries are encoded in the import-linter layered contract from commit #1, so
the relationship has to be pinned now.

## Decision

In the layered contract, place `config` immediately **above** `common`:

- `config` may import `common`.
- nothing higher may be imported *by* `common` or `config` (they sit at the
  bottom of the stack).

This sharpens §6's wording to: "`common` and `config` sit at the bottom; `config`
may use `common`."

## Consequences

- `import-linter` permits `config → common` and forbids `config → anything-higher`,
  matching the §6 intent without a special-case exception.
- No import cycles are possible through `config`/`common`.
