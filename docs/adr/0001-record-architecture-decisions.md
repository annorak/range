# 1. Record architecture decisions

Date: 2026-05-29

## Status

Accepted

## Context

We need a durable, reviewable record of the architectural decisions on this
project. The headline decisions D1–D9 are tabulated in
`docs/RANGE_DESIGN_V1.md` §5; decisions made or sharpened during the build need a
home too.

## Decision

We use Architecture Decision Records (ADRs), per
[Michael Nygard's pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions),
stored in `docs/adr/` as numbered Markdown files (`NNNN-title.md`). One ADR per
non-obvious decision; a step that makes such a decision adds its ADR in the same
PR.

## Consequences

- Decisions are version-controlled and reviewed alongside the code they justify.
- A reader can trace *why* a structure exists without spelunking commit history.
- ADRs are immutable once accepted; a later decision that overrides one adds a new
  ADR marking the old one superseded.
