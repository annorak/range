# Range

**Range** is a declarative, ephemeral, AI-native cyber-range platform. It turns
multi-host security simulations from bespoke, months-long engagements into a
config file plus parallel runs — built on top of [Inspect AI](https://inspect.ai-safety-institute.org.uk/),
with a backend-agnostic provisioner (containers + gVisor for v1), multi-agent
orchestration, a unified trace layer, and defense A/B as first-class primitives.

The product is **Range**; the Python import package is `rangelab`; the CLI is `range`.

## Quickstart

Requires [`uv`](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv sync          # create the venv and install deps
make check       # ruff + mypy --strict + import-linter + pytest (coverage ≥90%)
uv run range --version
```

## Make targets

| Target         | What it runs                                          |
|----------------|-------------------------------------------------------|
| `make install` | `uv sync`                                             |
| `make lint`    | `ruff check` + `ruff format --check`                  |
| `make fmt`     | `ruff format`                                         |
| `make types`   | `mypy` (strict)                                       |
| `make imports` | `import-linter` (enforces the package boundaries)     |
| `make test`    | `pytest` with the coverage gate                       |
| `make check`   | all of the above — the CI gate                        |

## Design

See [`docs/RANGE_DESIGN_V1.md`](docs/RANGE_DESIGN_V1.md) for the full v1 design,
and [`docs/steps/`](docs/steps/) for the per-step build plan. Engineering
standards every step follows live in
[`docs/steps/_SHARED_STANDARDS.md`](docs/steps/_SHARED_STANDARDS.md).
