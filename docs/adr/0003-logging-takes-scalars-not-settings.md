# 3. `configure_logging` takes scalars, not a `Settings` object

Date: 2026-05-29

## Status

Accepted

## Context

Step 0.2's notes give `configure_logging(settings: Settings) -> None`, with the
function living in `common/logging.py`. But `config` sits one layer **above**
`common` in the import layering (§6, ADR 0002, enforced by the import-linter
layered contract). Having `common.logging` import `config.Settings` — even only
for a type annotation — is an upward import that the boundary forbids and that CI
would reject.

The two ways to keep the literal `settings` parameter both have costs: importing
`Settings` under `TYPE_CHECKING` still trips the layered contract (or needs a
special-case `ignore_imports`, which ADR 0002 deliberately avoided), and a
`LoggingSettings` Protocol in `common` adds an abstraction for a single concrete
implementation — an anti-pattern under our YAGNI/KISS bar.

## Decision

`configure_logging` accepts the two rendering knobs it actually uses, as keyword
scalars:

```python
def configure_logging(*, log_format: Literal["console", "json"], log_level: str = "INFO") -> None
```

Callers (which already live above `config`) do:

```python
configure_logging(log_format=settings.log_format, log_level=settings.log_level)
```

## Consequences

- `common` imports nothing internal, so the layered contract stays green with no
  exceptions.
- No abstraction is introduced for a single caller; the dependency is explicit and
  the function is trivially testable without a `Settings` instance.
- This sharpens the Step 0.2 note; the `configure_logging` contract name is
  unchanged, only its parameters.
