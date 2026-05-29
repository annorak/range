# Range — Shared Engineering Standards

**Read this once before any step.** Every step file assumes these rules and only
restates step-specific additions. This is the §7/§8 contract of
`docs/RANGE_DESIGN_V1.md`, plus the code-quality bar for the whole repo.

---

## Code-quality bar (non-negotiable)

- **DRY / YAGNI / KISS.** Build exactly what the step asks for — no speculative
  abstraction, no "might need it later" hooks, no config knobs nobody requested.
  If two places need the same logic, factor it once; otherwise don't pre-factor.
- **Surgical & minimal.** Touch only what the step requires. Do not refactor,
  rename, or "tidy" unrelated code. A step's diff should read like a single
  focused change.
- **Skimmable & obvious.** A reader should understand each function at a glance:
  small, single-purpose, well-named. Prefer clarity over cleverness. If a piece
  needs a comment to be understood structurally, it's probably too complex.
- **Comment style — short-hand, why-not-what.** Public modules/classes/functions
  get a one-line docstring (longer only when the contract is non-obvious). Inline
  comments are brief and explain *why* (a non-obvious choice, a gotcha, a
  reference), never narrate *what* the code plainly does. Let type hints and good
  names do the documenting. No comment noise.
- **Non-obvious decisions → ADR.** If you make a design choice a future reader
  would question, add a short `docs/adr/NNNN-title.md`.

Example of the comment style we want:

```python
def content_hash(obj: Mapping[str, Any]) -> str:
    """Stable sha256 of a JSON-canonicalizable object (key order irrelevant)."""
    # sort_keys makes the hash invariant under dict reordering — this is the
    # property scenario_id relies on, so do not "optimize" it away.
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
```

---

## Language, tooling, layout

- **Python 3.12**, managed by **`uv`**. No global mutable state except the
  configured logger and the settings object.
- **`src` layout**, distribution `range-lab`, import package `rangelab`, CLI
  `range`. Package boundaries per §6 are enforced by **import-linter** in CI.
- **Dependencies are added per-step.** Each step lists the deps it introduces;
  add only those to `pyproject.toml`. This keeps every PR's dependency delta
  legible. Do not pre-add a library a later step will need.

## Typing & data

- Full type hints; **`mypy --strict`** passes.
- **Pydantic v2** for all external/config/spec data and anything serialized.
- Plain `@dataclass(slots=True)` for hot internal structs that are never
  serialized.

## Lint / format

- **`ruff`** (lint + format) clean. **`import-linter`** clean.

## Errors

- Typed hierarchy rooted at **`RangeError`** (`common/errors.py`):
  `SpecError`, `ProvisionError`, `BackendError`, `TraceError`, `ScoringError`,
  `RunError`, `ConfigError`.
- **No bare `except`.** User-facing failures carry a stable `code` and a
  `hint`. Run *outcomes* are result objects, never exceptions-as-control-flow.

## Logging

- **`structlog`**, key-value. JSON renderer in `prod`, console in `local`/`ci`.
- Every log line auto-carries the active correlation IDs (via contextvars).
- Secrets are redacted by a logging processor. **No `print`** anywhere.

## Config

- **`pydantic-settings`**, 12-factor. Load order: defaults → file (`RANGE_CONFIG`)
  → env (`RANGE_*`). Named profiles: `local`, `ci`, `prod`. Secrets are
  `SecretStr`; never logged, never baked into images.

## Dependency injection

- Backends, trace stores, and model providers are **Protocols/ABCs** resolved via
  a registry + factory; constructors take their dependencies explicitly. This is
  what lets the core be tested without Docker or cloud.

## Determinism (a property, not a component)

- Seeded RNG threaded explicitly (`Random(seed)`), never module-global `random`.
- Images referenced **by digest**; scenarios **content-addressed** (sha256 of the
  canonical spec). Same spec + seed ⇒ reproducible result.

## Security defaults

- Range containers run under **gVisor (`runsc`)**, `no-new-privileges`, dropped
  caps, read-only rootfs where feasible, resource limits set, and **no internet
  egress** unless the scenario explicitly allowlists it. Offensive tooling only
  ever runs *inside* the provisioned range, never on the control plane.
  *(Relevant from Epic 2 onward; listed here for completeness.)*

## Correlation IDs & one timeline (§8)

- The join keys for everything: `run_id` (ULID), `scenario_id` (content hash),
  `arm_id` (default `"control"`), `agent_id`, `host_id`, `step_seq`. Defined once
  in `common/ids.py`; identical across all capture sources.
- All events order on a hybrid clock `(wall_clock_utc, step_seq, source_seq)` —
  wall for humans, the counters for deterministic ordering when wall clocks
  collide.

## Testing

- **`pytest`**. **≥90% line coverage on core packages** (`spec`,
  `provision/base`, `trace`, `scoring`); `common` aims for 100%.
- **`hypothesis`** property tests where noted (round-trips, invariants,
  determinism, monotonicity).
- Integration tests gated by markers: `@pytest.mark.docker`,
  `@pytest.mark.postgres`. They **skip automatically** when the infra/`runsc` is
  absent (so plain CI stays green); a `runc`-hardened fallback path is tested
  where applicable.
- **E2E** (introduced in 8.4) runs the golden path on the **fake backend in CI**
  (always) and on **Docker locally/nightly** (full fidelity).
- CI gates that must pass to merge: `ruff`, `mypy --strict`, `import-linter`,
  unit + available integration, coverage ≥90% on core. **The coverage ratchet
  only goes up.**

## Git / PR

- Conventional commits. **One step = one PR.** CI green to merge. No merging
  contract-breaking TODOs. Each PR updates the docs/ADRs it touches.

---

## Target environment (v1)

- **Runtime host:** an **OCI x86 VM** (Ubuntu 24.04, paid shape — *not* the ARM
  Always-Free tier, so all standard x86 container images work) with Docker +
  `runsc` installed and Range running with the privileges it needs.
- **CI:** GitHub Actions on `ubuntu-latest` (x86), Python 3.12 via `uv`. gVisor
  integration tests run on the OCI box / nightly; they skip in plain CI.
- **Control plane and execution substrate are co-located on this one host for
  v1** (the split into separate workers comes with the parallel run controller,
  Epic 7). The agents are lightweight processes that call model-provider APIs;
  no GPU is required on the host.

---

## Infrastructure as Code (Terraform → OCI)

All OCI resources are managed by **Terraform** under `deploy/terraform/`. The
infra grows **incrementally and surgically, the same as the code**: the host is
stood up once (Step 0.3), and each later step that needs a new resource adds only
that resource. Never hand-create OCI resources in the console — if it isn't in
Terraform, it doesn't exist.

- **Module layout:** `deploy/terraform/` with `versions.tf` (pinned providers +
  `required_version`), `variables.tf`, `outputs.tf`, `network.tf`, `compute.tf`,
  `main.tf`, and `cloud-init/` for bootstrap files. Keep it a single flat
  root module for v1 (no premature module-nesting — YAGNI); factor into child
  modules only when a resource set is reused.
- **Two IaC layers, each doing what it's best at:**
  - **Terraform** (`deploy/terraform/`) owns **OCI cloud resources** — VCN/subnet/
    NSG/instance/block volume, and optional object storage. Reviewed via
    `terraform plan`, applied by the operator.
  - **docker-compose** (`deploy/compose/`, introduced in 4.2) owns **long-lived
    on-host service containers** — e.g. Postgres for the trace index. These are
    containers on the host, not cloud resources, so compose (declarative,
    version-controlled, `docker compose up -d`) is the right tool, not the
    Terraform-docker-over-SSH provider. Per-run *range* containers are still
    driven by the provisioner SDK (Epic 2), not compose.
  Secrets for compose services live in a git-ignored `deploy/compose/.env` (commit
  `.env.example`); bind service ports to `127.0.0.1` (defense in depth behind the
  NSG). Promoting an on-host service to a managed OCI offering (e.g. managed
  PostgreSQL) is a backlog item, not a v1 default.
- **Provider:** `hashicorp/oci`, version-pinned in `versions.tf`. Auth via the
  operator's `~/.oci/config` (API-key) — **never** commit keys or OCIDs of
  secrets.
- **No secrets in state or VCS.** Real values live in a git-ignored
  `terraform.tfvars`; commit a `terraform.tfvars.example`. Mark sensitive
  variables/outputs `sensitive = true`. State may contain sensitive data — local
  state stays out of git (`.gitignore`); a remote OCI Object Storage backend is a
  later hardening step (backlog B-32).
- **Tag everything** with common `freeform_tags`:
  `{ project = "range", env = var.env, managed_by = "terraform" }`.
- **CI:** an `infra` job runs `terraform fmt -check`, `terraform validate`, and
  (optional) `tflint`. CI **never** runs `apply` — applies are an operator action.
- **Per-step discipline:** a step that changes infra updates `deploy/terraform/`,
  is reviewed with `terraform plan`, applied by the operator, and then verified by
  a documented post-apply smoke check. This is how we "test as we go": the
  resource exists and is proven before the code that depends on it merges.
- **Cost:** the dev host is **stoppable** — stop it when idle (you then pay only
  for boot/block-volume storage). Document the stop/start commands; don't leave
  compute running between sessions.

### Make targets (added in 0.3, used by every infra-touching step)

```make
tf-init:     ; cd deploy/terraform && terraform init
tf-fmt:      ; cd deploy/terraform && terraform fmt
tf-validate: ; cd deploy/terraform && terraform fmt -check && terraform validate
tf-plan:     ; cd deploy/terraform && terraform plan
tf-apply:    ; cd deploy/terraform && terraform apply
tf-destroy:  ; cd deploy/terraform && terraform destroy
```

### On-host service targets (added in 4.2)

```make
services-up:   ; docker compose -f deploy/compose/services.yml up -d
services-down: ; docker compose -f deploy/compose/services.yml down
```

### Where integration tests run

Unit + fake-backend tests run anywhere (and in GitHub CI). The
`@pytest.mark.docker` / `@pytest.mark.gvisor` suites run **on the OCI host**
(develop there, or `ssh` in and `uv run pytest -m docker`), since they need
Docker + `runsc`. They skip automatically where that infra is absent, so CI stays
green. Putting a self-hosted runner on the host (backlog B-33) later lets those
run in CI too.
