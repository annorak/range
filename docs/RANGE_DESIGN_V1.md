# Range — v1 Design Document

> **Range** is a declarative, ephemeral, AI-native cyber-range platform. It turns
> multi-host security simulations from bespoke, months-long engagements into a
> config file plus parallel runs. It is built **on top of Inspect AI** for agent
> execution, with a **provisioner abstraction layer** (containers + gVisor now,
> VM/Firecracker later), **multi-agent orchestration** (attacker / defender /
> users), a **unified trace layer** (model + host + network telemetry on one
> timeline), **defense A/B** as a first-class primitive, and a **parallel run
> controller**.

---

## 0. How to read this document

This doc has three audiences:

1. **You (the author/architect)** — sections 1–8 define the product, the
   decisions, and the engineering contract.
2. **A coding agent** — section 9 is the build plan. Every step is sized to a
   single focused coding session (≈ ≤200k tokens of agent work: one coherent PR
   that ends with green tests). Each step lists goal, scope, granular
   implementation detail, the contracts it produces, testing, standards notes,
   dependencies, and a definition of done.
3. **A reviewer at Irregular / a partner lab** — section 2 (vision), section 5
   (decisions & rationale), and section 10 (the MVP demo) are written to be read
   cold.

A companion document, `RANGE_FUTURE_DEVELOPMENT.md`, holds everything beyond v1
plus a running "improvements backlog" (e.g. ClickHouse, Kafka, the VM-fidelity
backend, Windows/AD, a web UI). Diagrams referenced here are exported as SVGs:
`range-architecture-v1.svg`, `range-trace-pipeline.svg`,
`range-provisioner-abstraction.svg`, `range-run-lifecycle.svg`,
`range-build-map.svg`.

**Terminology note:** the product is "Range"; the Python import package is
`rangelab` (the bare word `range` is a Python builtin and a poor module name);
the CLI command is `range`.

---

## 1. The problem Range exists to solve

The frontier-AI cyber-evaluation ecosystem has converged on a narrow stack. The
**single-sandbox layer is solved**: almost everyone (Irregular, UK AISI, METR,
Apollo, US CAISI) runs evaluations on **Inspect AI**, whose sandboxing toolkit
ships Docker-Compose, Kubernetes, and Proxmox plugins for *one agent, one bounded
environment, one task*.

The **multi-host network-simulation layer is bespoke and painful.** This is where
the interesting work actually happens — and there is no product. The public
reference point is AISI's "The Last Ones" (TLO): a 32-step corporate-network
attack across four subnets and ~20 hosts, built as a contract by SpecterOps,
deployed as networked VMs with real Active Directory, real CI/CD pipelines, and a
Mythic C2. Building one range is a multi-month engineering project; that is why,
across the entire industry, only a small handful of ranges exist publicly.

The friction is **infrastructure, not research**, and the labs say so themselves:

- *"VM-based ranges provide realism that containerised approaches currently
  cannot match, but impose substantial engineering and operational overhead.
  Containerised environments with sufficient fidelity … could expand the scope
  and scale of evaluation."* (TLO future-work)
- **No active defenders.** Detections are recorded but cannot block, slow, or
  respond. There is no platform to fight an attacker model against a defender
  model under realistic counter-pressure.
- **OpsEc scoring is "too early-stage."** Alerts are counted but there is no
  baseline and no robust metric. (Independently, Irregular has said anomaly
  detection is going to break because nobody has a baseline.)
- **Reproducibility / replay / hermeticity** of multi-host ranges is manual.
- **Cost & spin-up** are high: a single 100M-token TLO attempt is ~$80 in
  inference alone; a 20-host VM topology takes minutes-to-hours to provision.
- **Defense A/B** ("insert or remove a defense and see what changes") is a manual
  environment rebuild per arm today.

Range is the engineering substrate that turns the bespoke work into a config file
and a parallel run.

---

## 2. Long-term product vision (the north star)

A team that wants to measure or harden AI cyber capability should be able to:

1. **Describe** a target environment declaratively — subnets, hosts, services,
   vulnerabilities, identities, defenders, and flag-scored milestones — in a
   versioned spec, composing from a library of reusable building blocks.
2. **Provision** it instantly and ephemerally on whichever fidelity tier the
   scenario needs, via a single backend-agnostic interface: containers + gVisor
   for stateless hosts, microVMs/VMs for kernel-level fidelity (real EDR, real
   AD), cloud for scale — mixed *hybrid* within one range.
3. **Populate** it with any number of AI agent roles — attacker(s), defender(s),
   neutral "users" generating realistic noise — each with its own model,
   toolbox, and scaffold, mediated by a policy engine.
4. **Observe** everything on **one timeline**: model reasoning and tool calls,
   host process/auth/file/EDR events, and network PCAP/flow/DNS — correlated,
   queryable, and replayable.
5. **Experiment**: toggle defenses per arm, run identical environments
   side-by-side, and get OpsEc scoring (alerts-per-step, time-to-detection,
   progress-with-vs-without each control).
6. **Scale**: submit `(scenario, model, defense-config, N)` and have it
   provision, run in parallel, score against milestones, track token + infra
   cost, and produce reports — turning a TLO-class evaluation from a quarter of
   engineering into an afternoon.

The far horizon (future-dev doc): a hosted, multi-tenant SaaS + self-host
offering; a marketplace of community ranges; export of ranges as RL training
environments; digital-twin / ICS fidelity; and a web console.

---

## 3. v1 scope & non-goals

**v1 is a real, launchable, production-grade platform** covering the full loop at
**container + gVisor fidelity, Linux-only, CLI-driven**, with the architecture
explicitly designed so that higher-fidelity backends, more telemetry sources, and
a UI are *additive*, never rewrites.

**In v1 (sections 9, epics 0–8):**

- Declarative scenario spec + validation/linting + composable building blocks +
  milestone/flag scoring spec.
- Provisioner **abstraction layer** + an **in-memory fake backend** (for tests) +
  a **Docker + gVisor backend** + network fabric (subnets, routing, firewall,
  egress control) + golden-image build pipeline + snapshot/reset.
- **Inspect AI integration**: scenario → Inspect `Task`/`Sample`; a custom
  `SandboxEnvironment` bridging Range's provisioner to Inspect.
- **Agents**: attacker (ReAct + context compaction + toolbox), defender, neutral
  users; a **multi-agent orchestrator** with a turn/scheduling model and an
  **inter-agent policy engine**.
- **Unified trace layer**: schema/event model, storage (Postgres index + S3/local
  Parquet), capture for model + host + network telemetry, DuckDB query + replay.
- **Defense A/B**: defense config + insertion, parallel arms on identical
  environments, OpsEc scoring + trace diff.
- **Run controller**: parallel `(scenario, model, defense, N)` runs, concurrency
  & resource management, cost tracking, results aggregation + reporting (Markdown
  / JSON + SVG milestone matrix).
- **Productionization**: a polished `range` CLI, Range self-observability (logs,
  metrics, health, audit), packaging/containerization + local full-stack compose,
  docs + a reference "Mini-Enterprise" range + a golden-path E2E test.

**Explicit non-goals for v1 (→ future-dev doc):**

- VM / Firecracker / libvirt / Proxmox / cloud provisioner backends (the
  abstraction is built; these are backend implementations added later).
- Windows / Active Directory fidelity (Linux-only in v1).
- ClickHouse + Kafka ingestion (Postgres + S3/Parquet + DuckDB is the v1 store;
  migration is a future step).
- Web UI / hosted multi-tenant SaaS / auth & RBAC / billing.
- ML-heavy transcript clustering / learned failure-mode taxonomies (v1 ships
  deterministic stats + matrices; richer analytics later).
- ICS / digital-twin / OT ranges.

---

## 4. Architecture overview

See `range-architecture-v1.svg` for the full picture (MVP elements solid green,
remaining-v1 solid blue, future elements dashed amber). At a glance, six planes:

- **Interface plane** — the `range` CLI + config/profiles. (Web UI is future.)
- **Control plane** — the **Run Controller** (schedules N parallel runs, tracks
  lifecycle/cost), the **A/B Harness**, and the **Orchestrator** (drives agent
  roles through a scenario).
- **Execution plane** — the **Inspect bridge** (`Task`/`Sample` + custom
  `SandboxEnvironment`) and the **agents** (attacker / defender / users).
- **Provisioning plane** — the **provisioner abstraction** with the **Docker +
  gVisor backend**, the **network fabric**, **golden images**, and
  **snapshot/reset**. (VM/cloud backends slot in behind the same interface.)
- **The Range** — the provisioned, isolated, multi-host environment under test.
- **Trace plane** — **capture** (model + host + network) → **store** (Postgres
  metadata/index + S3/Parquet events) → **query** (DuckDB) → **replay / report**,
  feeding **scoring** (flags/milestones + OpsEc).

Data flow for a single run is in `range-run-lifecycle.svg`; the telemetry pipeline
is in `range-trace-pipeline.svg`; the backend-abstraction story is in
`range-provisioner-abstraction.svg`; the build order and MVP cut are in
`range-build-map.svg`.

---

## 5. Key design decisions & rationale

| # | Decision | Rationale | Reversal cost |
|---|----------|-----------|---------------|
| D1 | **Python 3.12** for the entire control plane, spec, orchestrator, agents, trace, CLI. | Inspect AI is a Python framework — building "on top of Inspect" effectively mandates Python; the whole eval ecosystem and all the labs are Python. Java would force shelling out to / reimplementing Inspect. | High (would orphan the Inspect bet). |
| D2 | **Build on top of Inspect AI** as the agent-execution and sandbox-protocol substrate, rather than a standalone engine. | Instant ecosystem credibility (Irregular/AISI/METR/Apollo already use it); huge surface we don't have to build (solvers, tool plumbing, transcripts, model providers, compaction patterns); we'd have to integrate eventually anyway. We add the *multi-host, multi-agent, unified-trace, defense-A/B* layer Inspect lacks. | Medium (our value-add lives above Inspect; could be re-hosted). |
| D3 | **Provisioner abstraction layer first; Docker + gVisor as the v1 backend.** VM/Firecracker/libvirt/Proxmox/cloud are future backend implementations behind the same interface. | No-tech-debt path: ships fast on containers, makes higher-fidelity tiers additive. Matches AISI's own "containerised environments with sufficient fidelity" future-work. | Low by design (a backend is a swap, not a rewrite). |
| D4 | **Container + gVisor fidelity, Linux-only, for v1.** | Avoids Windows licensing/host requirements now; gVisor gives strong isolation for running offensive tooling. Windows/AD + VM fidelity is a clearly-scoped free-via-eval future step. | Low (new backend + new image family). |
| D5 | **Trace store = Postgres (metadata/index) + S3-or-local Parquet (events) + DuckDB (query).** | Simplest thing that is genuinely production-shaped and scales far past demo needs; no cluster to operate. Kafka ingestion + ClickHouse analytical store are future steps with a migration path designed in (append-only, schema-versioned events). | Low–Medium (store behind a `TraceStore` interface; migration is a backfill). |
| D6 | **CLI-first; no web UI in v1.** | Matches how labs actually run evals; fastest credible path; the control plane is a library the CLI calls, so a UI is additive. | Low. |
| D7 | **Determinism & hermeticity are first-class:** images pinned by digest, scenarios content-addressed, seeded RNG, no implicit internet. | Reproducibility is a named industry pain (high run-to-run variance ⇒ many runs ⇒ cost). Treating it as a property, not an afterthought, is the differentiator. | n/a (a property, not a component). |
| D8 | **Every backend / store / model-provider is injected behind a Protocol/ABC via a registry.** | Keeps the core testable without Docker/cloud (the fake backend), and keeps D3/D5 cheap to extend. | n/a. |
| D9 | **All OCI infrastructure is managed by Terraform (`deploy/terraform/`), introduced in 0.3 and grown incrementally per step.** v1 runs on a single paid **OCI x86 VM** (Docker + `runsc`); the control plane and execution substrate co-locate there. | "Test as we go" needs the substrate to be reproducible and version-controlled from the first infra need; x86 (not the ARM free tier) avoids image-compatibility friction; incremental TF keeps infra changes as surgical as code changes. | Low (provider-specific resources; the host/runtime contract is portable, and a managed-sandbox/cloud backend is a future swap — backlog B-29). |

Architecture Decision Records live in `docs/adr/` (one ADR per decision above,
plus any added during the build).

---

## 6. Repository layout & package boundaries

`src` layout, single distribution `range-lab`, import package `rangelab`.

```
range/
├── pyproject.toml                # uv-managed; ruff, mypy, pytest config
├── uv.lock
├── README.md
├── docs/
│   ├── adr/                      # architecture decision records
│   ├── RANGE_DESIGN_V1.md
│   ├── RANGE_FUTURE_DEVELOPMENT.md
│   └── diagrams/                 # the exported SVGs
├── examples/
│   └── scenarios/                # reference ranges (mini-enterprise, …)
├── src/rangelab/
│   ├── common/                   # errors, logging, ids, shared types, time
│   ├── config/                   # pydantic-settings: env + file + profiles
│   ├── spec/                     # scenario models, loader, validation, milestones, fragments
│   ├── provision/
│   │   ├── base.py               # Backend Protocol, lifecycle SM, handles
│   │   ├── fake.py               # in-memory backend (tests)
│   │   ├── docker/               # Docker + gVisor backend
│   │   ├── network.py            # subnets/router/firewall/egress
│   │   ├── images.py             # golden-image build + cache + vuln/flag injection
│   │   └── snapshot.py           # snapshot/restore/reset
│   ├── inspect_bridge/           # scenario→Task/Sample; Range SandboxEnvironment
│   ├── agents/                   # attacker, defender, users, tools, compaction
│   ├── orchestrator/             # multi-agent core, scheduler, policy engine
│   ├── trace/                    # schema, store, model/host/net capture, query, replay
│   ├── scoring/                  # flags, milestones, opsec, result models
│   ├── run/                      # single-run path, controller, A/B, worker pool
│   ├── report/                   # aggregation, markdown/json render, svg matrix
│   ├── telemetry/                # in-range collectors + Range's own metrics
│   └── cli/                      # `range` command + subcommands
└── tests/
    ├── unit/
    ├── integration/              # @pytest.mark.docker etc.
    └── e2e/
```

**Boundary rules:** `common` and `config` depend on nothing internal. `spec` is
pure (no I/O, no Docker). `provision` depends on `spec` + `common`. `trace`
depends on `spec` + `common` only. `inspect_bridge` depends on `provision`,
`spec`. `agents` depend on `inspect_bridge` + `trace`. `orchestrator` depends on
`agents` + `provision` + `trace`. `run` depends on everything below it.
`report` depends on `trace` + `scoring`. `cli` depends on `run`, `report`,
`spec`. No upward imports; no cycles (enforced in CI with `import-linter`).

---

## 7. Global engineering standards (the contract every step follows)

These apply to **every** step; steps only restate *additional* step-specific
notes.

- **Language/runtime:** Python 3.12, managed by **`uv`**. No global state except
  the configured logger and settings object.
- **Typing:** full type hints; **`mypy --strict`** must pass. **Pydantic v2** for
  all external/config/spec data and all serialized records; plain
  `@dataclass(slots=True)` for hot internal structs.
- **Lint/format:** **`ruff`** (lint + format) clean; **`import-linter`** enforces
  the boundary rules in §6.
- **Async:** orchestrator, run controller, and any backend I/O are `asyncio`;
  blocking calls (Docker SDK, subprocess) wrapped via `asyncio.to_thread` or an
  executor. `pytest-asyncio` for async tests.
- **Errors:** a typed hierarchy rooted at `RangeError`
  (`SpecError`, `ProvisionError`, `BackendError`, `TraceError`, `ScoringError`,
  `RunError`, …). No bare `except`. User-facing failures carry a stable
  `code` and a remediation hint. Run outcomes are **result objects**, never
  exceptions-as-control-flow.
- **Logging:** **`structlog`**, key-value, JSON renderer in prod / console in
  dev. Every log line carries the active correlation IDs (see §8). **No `print`.**
- **Config:** **`pydantic-settings`**; 12-factor; env overrides file; named
  **profiles** (`local`, `ci`, `prod`). Secrets never logged, never baked into
  images.
- **Dependency injection:** backends, trace stores, and model providers are
  **Protocols/ABCs** resolved via a `registry` + factory; constructors take
  dependencies explicitly. This is what makes the core testable without Docker.
- **Determinism:** seeded RNG (`Random(seed)` threaded through, no module-global
  `random`); images referenced **by digest**; scenarios **content-addressed**
  (sha256 of the canonicalized spec). Provisioning of the same spec + seed is
  reproducible.
- **Security defaults:** containers run under the **gVisor (`runsc`)** runtime,
  **no new privileges**, dropped capabilities, read-only rootfs where feasible,
  resource limits set, and **no internet egress** unless the scenario explicitly
  allowlists it.
- **Testing:** **`pytest`**; **≥90% line coverage on core packages** (`spec`,
  `provision/base`, `trace`, `scoring`); integration tests gated by markers
  (`@pytest.mark.docker`, `@pytest.mark.postgres`); **`hypothesis`** property
  tests for spec validation and trace round-trips. CI gates: ruff, mypy,
  import-linter, unit + (where infra available) integration, coverage threshold.
- **Git/PR:** conventional commits; **one step = one PR**; CI green to merge; no
  merging contract-breaking TODOs. Each PR updates docs/ADRs it touches.
- **Docs:** every public module/class has a docstring; non-obvious decisions get
  an ADR.

---

## 8. Cross-cutting concerns

- **Correlation IDs.** Every event and log line is tagged with a stable ID set:
  `run_id` (ULID), `scenario_id` (content hash), `arm_id` (A/B arm, default
  `"control"`), `agent_id` (role instance), `host_id` (logical host name from the
  spec), and a monotonically increasing `step_seq` per run. These are the join
  keys for the unified trace; they are defined once in `common/ids.py` and are
  non-negotiable across all capture sources.
- **One timeline.** All capture sources emit into a single ordered event stream
  keyed by a hybrid logical clock: `(wall_clock_utc, step_seq, source_seq)`. Wall
  clock for human reading; `step_seq`/`source_seq` for deterministic ordering when
  wall clocks collide or skew.
- **Isolation & safety.** The range is the blast radius. Defaults: no egress,
  gVisor, dropped caps. Any scenario that opens egress must do so explicitly and
  is flagged in the run record. Offensive tooling only ever runs *inside* the
  provisioned range, never on the control plane.
- **Secrets.** Model-provider keys and store credentials come from the
  environment / secret store via `config`; never written to images, traces, or
  logs (a redaction filter in `common/logging.py` scrubs known key shapes).
- **Cost.** Token usage (per model call) and infra time (per host, per run) are
  captured as first-class trace metrics and surfaced in the run record and
  reports.
- **Self-observability.** Range emits its own structured logs + Prometheus
  metrics (run counts, provision durations, backend errors, queue depth) and a
  per-run audit log — distinct from the *in-range* telemetry it captures.
- **Infrastructure as code.** Every OCI resource is declared in Terraform
  (`deploy/terraform/`) and grown incrementally per step (D9): the host in 0.3,
  then only what each later step needs. No console-created resources; infra
  changes are reviewed via `terraform plan`, applied by the operator, and proven
  by a post-apply smoke check before the dependent code merges. Secrets never
  enter state or VCS.

---

## 9. The build plan — epics & steps

Each step is tagged **[MVP]** (part of the naive demo, §10) or **[v1]**
(remaining v1). Steps are ordered to respect dependencies; the critical path is
in §11 and `range-build-map.svg`. Template fields per step: **Goal**, **Scope**,
**Out of scope**, **Implementation**, **Contracts produced**, **Testing**,
**Standards notes**, **Depends on / Blocks**, **Done when**.

---

### Epic 0 — Foundations

#### Step 0.1 — Repository scaffold, tooling, CI  **[MVP]**
- **Goal:** A clean, type-checked, lint-clean, testable skeleton that CI enforces
  from commit #1.
- **Scope:** `pyproject.toml` (uv) with deps pinned; `src/rangelab` package skeleton
  with the §6 subpackages as empty `__init__.py` + module stubs; ruff + mypy
  (strict) + pytest + coverage + import-linter configs; `pre-commit` hooks;
  GitHub Actions workflow running ruff/mypy/import-linter/pytest/coverage-gate; a
  trivial `range --version` entrypoint; `README` quickstart.
- **Out of scope:** any real feature logic.
- **Implementation:** console_scripts entry `range = "rangelab.cli.main:app"`
  (Typer app stub). import-linter contracts encode §6 boundaries. CI matrix:
  Python 3.12; jobs `lint`, `types`, `unit`. Coverage gate starts at 90% (trivial
  to meet on a skeleton; ratchet never lowers). Add a `Makefile`/`uv` task aliases
  (`uv run lint`, `uv run types`, `uv run test`).
- **Contracts produced:** the package layout + the CI gate every later step must
  keep green.
- **Testing:** one smoke test asserting `range --version`; CI itself is the test.
- **Standards notes:** establishes the §7 contract physically.
- **Depends on:** —. **Blocks:** everything.
- **Done when:** fresh clone → `uv sync` → all CI tasks pass locally and in CI.

#### Step 0.2 — Core primitives: ids, logging, errors, config, time  **[MVP]**
- **Goal:** The shared substrate every package imports.
- **Scope:** `common/ids.py` (ULID `run_id`/`agent_id`, content-hash helper for
  `scenario_id`, `step_seq` counter, the `CorrelationIds` model);
  `common/logging.py` (structlog setup, JSON/console renderers, secret-redaction
  filter, contextvar binding of correlation IDs); `common/errors.py` (the
  `RangeError` hierarchy from §7); `common/time.py` (UTC now, the hybrid
  `LogicalClock` producing `(wall, step_seq, source_seq)`); `config/settings.py`
  (pydantic-settings: model-provider keys, store URLs/paths, profiles, log level).
- **Out of scope:** anything that does I/O against real systems.
- **Implementation:** correlation IDs propagate via `contextvars` so log lines and
  emitted events auto-tag. Redaction filter regexes known key shapes
  (`sk-…`, `AKIA…`, bearer tokens). `LogicalClock` is monotonic per process and
  seedable for tests. Settings load order: defaults → file (`RANGE_CONFIG`) → env
  (`RANGE_*`).
- **Contracts produced:** `CorrelationIds`, `RangeError`, `get_logger()`,
  `Settings`, `LogicalClock` — imported everywhere.
- **Testing:** unit: ID uniqueness/sortability; redaction scrubs sample secrets;
  clock monotonicity + determinism under seed; settings precedence. Hypothesis:
  content-hash stability under dict reordering.
- **Standards notes:** this is where §7 logging/errors/config become real.
- **Depends on:** 0.1. **Blocks:** all.
- **Done when:** other packages can import these; 100% coverage on `common`.

#### Step 0.3 — Infrastructure foundation: Terraform + OCI host  **[MVP]**
- **Goal:** A reproducible, version-controlled **OCI x86 host** (Docker + `runsc`
  + Python/uv), provisioned by Terraform, that all Docker-backed integration tests
  target — and the IaC foundation every later infra need extends (D9).
- **Scope:** `deploy/terraform/` root module — provider/versions (pinned
  `hashicorp/oci`), a VCN + internet gateway + route table + subnet + a
  locked-down NSG (SSH from operator IP only; egress 443/DNS), an x86 flex
  **compute instance** (Ubuntu 24.04) with an SSH key + cloud-init, and a block
  volume + attachment for trace/state. `cloud-init/bootstrap.yaml` installs Docker
  CE, **gVisor `runsc`** (apt repo + `daemon.json` runtime registration), Python
  3.12 + uv (and optionally Tailscale). `variables.tf` (region, compartment,
  shape, ocpus/memory, ssh key, allowed CIDR), `outputs.tf` (public IP),
  `terraform.tfvars.example`. A CI `infra` job (`fmt -check` + `validate`; never
  `apply`). `Makefile` `tf-*` targets. ADR recording the IaC choice.
- **Out of scope:** any Range *application* resource beyond the host (Postgres,
  object storage, OCIR) — added by the steps that need them (Epic 4, 2.5). Remote
  TF state and a self-hosted CI runner are hardening backlog items (B-32, B-33).
- **Implementation:** x86 flex shape (e.g. `VM.Standard.E4.Flex`, ~4 OCPU/24–32 GB)
  — **not** the ARM Always-Free tier, so standard x86 images work. Host stays
  **stoppable** for cost. Range runs with the privileges it needs; range isolation
  is enforced in-Docker (Epic 2.3/2.4), separate from the host NSG. Note the
  `runsc` + Docker embedded-DNS caveat that 2.3 must handle (backlog B-30).
- **Contracts produced:** the `deploy/terraform/` module + outputs (host IP/SSH);
  the bootstrapped runtime (Docker + `runsc` + uv) that 2.2+ integration tests
  target; the `tf-*` make targets + CI `infra` job; the per-step infra workflow.
- **Testing:** CI: `terraform fmt -check` + `validate` (+ optional `tflint`).
  Operator post-apply smoke (documented/scripted, needs real creds): SSH in;
  `docker info` shows the `runsc` runtime; `docker run --runtime=runsc --rm
  hello-world` works; `uv --version` works; `terraform destroy` tears it down.
- **Standards notes:** infra is code — DRY/surgical/skimmable; no secrets in state
  or VCS; tag every resource (§ shared standards, IaC section).
- **Depends on:** 0.1. **Blocks:** 2.2 (Docker integration tests), 2.3–2.6, 4.2
  (trace store on host), and all later infra.
- **Done when:** `terraform apply` stands up the host; the runsc smoke checks pass;
  `fmt`/`validate` are green in CI; `terraform destroy` cleans up.

---

### Epic 1 — Scenario spec

#### Step 1.1 — Scenario spec schema + YAML loader  **[MVP]**
- **Goal:** A typed, versioned description of a range that humans write and the
  system parses.
- **Scope:** Pydantic v2 models in `spec/models.py`:
  `Scenario{apiVersion, metadata, network, hosts, identities, defenses?,
  milestones, scoring}`; `Subnet{name, cidr}`; `Host{name, subnet, image,
  role(enum: entry|server|workstation|router|target), services[], files[],
  env, resources}`; `Service{name, type, port, config}`; `Identity{username,
  secret_ref, locations[]}`; `FileArtifact{path, content_ref|content, mode,
  is_flag, flag_id?}`. Loader in `spec/loader.py` (YAML → models, with helpful
  error locations). Canonicalization → `scenario_id` (content hash). JSON Schema
  export for editor tooling.
- **Out of scope:** semantic validation (1.2), milestone/scoring semantics (1.3),
  building-block composition (1.3).
- **Implementation:** `apiVersion: range/v1alpha1`. `secret_ref`/`content_ref`
  are indirections resolved later (never inline real secrets). Resources default
  to small (0.5 CPU, 512MB). YAML parsed with `ruamel.yaml` to preserve line
  numbers for error messages. Round-trip (`Scenario.model_dump()` → YAML → load)
  is identity-stable.
- **Contracts produced:** `Scenario` and friends — the spine of the whole system;
  `scenario_id`.
- **Testing:** unit: load the reference mini-enterprise YAML; round-trip stability;
  malformed YAML yields a `SpecError` with line info. Hypothesis: random valid
  specs round-trip; `scenario_id` invariant under key reordering / comment
  changes.
- **Standards notes:** `spec` stays pure — no I/O beyond reading the passed text.
- **Depends on:** 0.2. **Blocks:** 1.2, 1.3, 2.x, 3.1.
- **Done when:** a representative YAML loads into typed models with a stable
  content hash.

#### Step 1.2 — Spec validation, linting & `range validate`  **[MVP]**
- **Goal:** Catch broken ranges before any compute is spent.
- **Scope:** `spec/validate.py` semantic checks: referential integrity (every
  `host.subnet` exists; every `identity.location` names a real host; every
  `flag_id` unique; milestone flag refs resolve); network sanity (subnets are
  valid non-overlapping CIDRs; host count fits the CIDR; exactly one `router` per
  multi-subnet network or an explicit gateway); image references are pinned
  (digest or explicit tag policy); resource sums within configured caps;
  egress-allowlist well-formed. A lint pass for warnings (host with no services,
  unreachable subnet, flag with no covering milestone). `range validate
  <file> [--strict]` CLI (Typer) with a human report + non-zero exit on errors.
- **Out of scope:** provisioning; runtime reachability (static checks only).
- **Implementation:** validators return a list of `Diagnostic{severity, code,
  loc, message, hint}`; `--strict` promotes warnings to errors. CIDR math via
  `ipaddress`. Reachability is a static graph check (subnets connected via
  router/gateway edges), not a live probe.
- **Contracts produced:** `validate(scenario) -> list[Diagnostic]`; the
  `Diagnostic` model (reused by reports).
- **Testing:** unit: a battery of intentionally-broken specs each trip the right
  code; a golden valid spec produces zero errors. CLI test via `typer.testing`.
- **Standards notes:** stable diagnostic `code`s (documented table) — they become
  an API.
- **Depends on:** 1.1. **Blocks:** 3.1 (provision rejects invalid specs), CLI.
- **Done when:** `range validate` passes the reference range and fails a curated
  broken set with correct codes.

#### Step 1.3 — Milestones, scoring spec & building-block fragments  **[MVP]**
- **Goal:** Define how progress is scored, and let specs compose from reusable
  parts.
- **Scope:** `spec/milestones.py`: `Milestone{id, title, flags[], requires[]
  (milestone deps), human_effort_estimate?}`; `Scoring{mode: sequential|
  independent, partial_credit: bool}`. Sequential-credit semantics (reaching a
  later flag credits prerequisite milestones) vs independent. `spec/fragments.py`:
  composable building blocks (e.g. `misconfigured-web-app`, `weak-cred-host`,
  `flat-subnet`) as parameterized partial specs, plus an `includes:` mechanism in
  the loader to merge fragments into a scenario with override rules.
- **Out of scope:** the scorer implementation (that's 3.3, which *consumes* this);
  OpsEc scoring (6.3).
- **Implementation:** milestone DAG validated (no cycles; `requires` resolve).
  Fragment merge is deep, deterministic, and order-independent for disjoint keys;
  conflicts are errors surfaced as `Diagnostic`s. Each fragment ships with its own
  mini JSON Schema and a doc snippet.
- **Contracts produced:** `Milestone`, `Scoring`, the fragment registry + merge —
  consumed by `scoring` and authors.
- **Testing:** unit: DAG cycle detection; sequential vs independent credit on a
  toy chain; fragment merge determinism (property test: permuting include order
  yields identical canonical spec for disjoint fragments).
- **Standards notes:** keep fragments pure data; no codegen.
- **Depends on:** 1.1, 1.2. **Blocks:** 3.3, 8.4.
- **Done when:** the reference range composes from ≥2 fragments and defines a valid
  milestone DAG.

---

### Epic 2 — Provisioner: abstraction + Docker/gVisor backend

#### Step 2.1 — Provisioner interface, lifecycle SM & fake backend  **[MVP]**
- **Goal:** The backend-agnostic contract (D3/D8) plus a real in-memory
  implementation so all downstream work is testable without Docker.
- **Scope:** `provision/base.py`: a `Backend` Protocol —
  `async provision(scenario, run_ctx) -> RangeHandle`,
  `async exec(handle, host_id, argv|script, *, timeout, user) -> ExecResult`,
  `async snapshot(handle) -> SnapshotId` / `async restore(handle, snap)`,
  `async teardown(handle)`, plus `async copy_in/out`. `RangeHandle`
  (opaque per-backend handle + resolved host map + network info). A `LifecycleSM`
  (`CREATED→PROVISIONING→READY→RUNNING→SNAPSHOTTED→TEARDOWN→DESTROYED`, illegal
  transitions raise). A `registry` mapping backend name → factory.
  `provision/fake.py`: an in-memory backend modeling hosts/networks/files as
  Python objects; `exec` runs a small built-in command interpreter (enough to
  satisfy orchestrator/agent tests: `ls`, `cat`, `whoami`, fake `nmap`, flag
  reads) deterministically.
- **Out of scope:** Docker (2.2), real networking (2.3).
- **Implementation:** every backend op takes/propagates `CorrelationIds` and emits
  lifecycle events to the trace sink (injected). Idempotent `teardown`. `exec`
  returns `ExecResult{stdout, stderr, exit_code, duration}`. The fake backend's
  interpreter is intentionally minimal but covers the agent/scorer/trace contracts.
- **Contracts produced:** `Backend`, `RangeHandle`, `ExecResult`, `LifecycleSM`,
  the registry — the seam the entire platform is built on.
- **Testing:** unit: lifecycle legal/illegal transitions; fake backend
  provision→exec→snapshot→restore→teardown; idempotent teardown; concurrent
  exec safety. This package is core ⇒ ≥90% coverage.
- **Standards notes:** **this is the most important interface in v1** — review it
  hard; it is what makes higher-fidelity backends additive.
- **Depends on:** 1.1, 0.2. **Blocks:** 2.2–2.6, 3.1, all orchestrator/run work.
- **Done when:** downstream code can target `Backend` and a full run works on the
  fake backend in tests.

#### Step 2.2 — Docker backend: hosts → containers  **[MVP]**
- **Goal:** Turn a scenario's hosts into real, isolated containers.
- **Scope:** `provision/docker/backend.py` implementing `Backend` over the Docker
  SDK: per-host container from the host's (digest-pinned) image; label every
  resource with `run_id`/`scenario_id` for discovery + cleanup; implement `exec`
  (via `container.exec_run` wrapped in a thread), `copy_in/out` (tar streams),
  `teardown` (stop+remove by label, idempotent). Health/readiness wait.
- **Out of scope:** networking/subnets (2.3), gVisor hardening (2.4), images
  (2.5), snapshot (2.6).
- **Implementation:** blocking SDK calls offloaded to a thread pool. Containers
  named `range-<run_id>-<host_id>`. Resource limits from spec applied
  (`nano_cpus`, `mem_limit`). Readiness = container running + optional per-host
  healthcheck. All failures wrapped as `BackendError` with the docker error code.
- **Contracts produced:** the first real `Backend`; container labeling/cleanup
  convention.
- **Testing:** `@pytest.mark.docker` integration: provision a 2-host scenario,
  exec `whoami`, copy a file in/out, teardown leaves nothing (verified by label
  query). Unit: argv building, label logic (mock SDK).
- **Standards notes:** never leak containers — teardown must be exhaustive by
  label even on partial provision failure (finalizer pattern).
- **Depends on:** 2.1. **Blocks:** 2.3, 2.4, 3.1, 4.4.
- **Done when:** a multi-host scenario stands up and tears down cleanly on Docker.

#### Step 2.3 — Network fabric: subnets, routing, firewall, egress  **[MVP]**
- **Goal:** Realistic multi-subnet topology with controlled reachability and no
  accidental internet.
- **Scope:** `provision/network.py`: create a Docker network per subnet (no
  default bridge); attach hosts to their subnet(s); stand up a **router container**
  bridging subnets with `iptables`-based forwarding + per-edge allow/deny policy
  from the spec; default-deny egress to the internet with an optional per-scenario
  allowlist (egress proxy or iptables rules); DNS within the range resolves host
  names. Wire this into the Docker backend's `provision`.
- **Out of scope:** eBPF policy (future), network telemetry capture (4.5).
- **Implementation:** networks are `internal: true` unless egress is allowlisted.
  Router runs a minimal image with IP forwarding; routes derived from the subnet
  graph; firewall rules generated from spec edges. Internal DNS via the router or
  an embedded resolver mapping `host_id`→IP. Static IP assignment per host for
  determinism.
- **Contracts produced:** the network info in `RangeHandle` (host IPs, subnet
  map); egress policy applied + recorded.
- **Testing:** `@pytest.mark.docker`: hosts in the same subnet reach each other;
  cross-subnet reachable only where policy allows; internet blocked by default;
  allowlisted host reachable; name resolution works. Unit: route/rule generation
  from a topology graph.
- **Standards notes:** egress-open scenarios set a flag on the run record (§8
  safety).
- **Depends on:** 2.2. **Blocks:** 2.4, 3.x, 4.5.
- **Done when:** the reference topology's reachability matrix matches the spec and
  egress is closed by default.

#### Step 2.4 — gVisor runtime + isolation hardening  **[MVP]**
- **Goal:** Run untrusted/offensive workloads under strong isolation by default.
- **Scope:** Run containers under the **`runsc` (gVisor)** runtime; apply
  `no-new-privileges`, dropped Linux capabilities (allowlist only what services
  need), read-only rootfs + explicit writable mounts, pids/ulimit/memory limits,
  and seccomp defaults. A capability profile per host `role`. Graceful fallback +
  clear error if `runsc` is unavailable (CI may lack it → mark those tests, keep a
  `runtime=runc` test path with hardening still applied).
- **Out of scope:** VM isolation (future backend).
- **Implementation:** runtime selected via config/profile (`prod`→runsc,
  `ci`→runc-with-hardening if runsc absent). Capability allowlists are per-role
  constants, overridable per host with justification. Document the gVisor syscall
  caveats (some tools behave differently) in an ADR.
- **Contracts produced:** hardened defaults applied to every container; a
  `SecurityProfile` per host.
- **Testing:** `@pytest.mark.gvisor` (skipped if runsc absent): container runs
  under runsc; `no-new-privileges` enforced (a setuid escalation attempt fails);
  dropped cap blocks a privileged op. Unit: profile→docker-arg mapping.
- **Standards notes:** isolation is a default, not an opt-in (§7/§8).
- **Depends on:** 2.2, 2.3. **Blocks:** 3.x (safe agent execution).
- **Done when:** every provisioned container is hardened; runsc used where present.

#### Step 2.5 — Golden-image build pipeline + vuln/flag injection  **[MVP]**
- **Goal:** Reproducible, fast-starting host images carrying services,
  vulnerabilities, and planted flags.
- **Scope:** `provision/images.py`: a build pipeline turning a host/service/vuln
  spec into a Dockerfile layer set; a small catalog of base service images
  (vulnerable web app, SSH host with weak creds, internal file server, a "kali"
  attacker image with common tools); a **vuln/flag injection** mechanism (planted
  files with `is_flag`, weak credentials from `identities`, misconfigurations from
  `service.config`); content-addressed image caching keyed by the resolved build
  inputs; digest pinning on output.
- **Out of scope:** Windows images (future); production-grade vuln libraries
  (future fragment expansion).
- **Implementation:** builds are hermetic (no network at build unless allowlisted;
  pinned apt/pip via a vendored cache where feasible). Cache key = sha256(base
  digest + layer inputs); a cache hit skips rebuild. Flags are generated
  deterministically from `(scenario_id, flag_id, seed)` so a re-provision yields
  the same flags (for reproducible scoring) unless `rotate_flags` is set. The
  attacker "kali" image is minimal (bash, python, nmap, curl, common libs) — the
  full pentest toolset is a future fragment.
- **Contracts produced:** `build_images(scenario) -> {host_id: image_digest}`;
  the flag-generation function (shared with the scorer).
- **Testing:** integration (docker): build the reference range's images; a planted
  flag is present at its path; weak cred logs in; cache hit on rebuild (no layers
  rebuilt). Unit: cache-key stability; deterministic flag generation.
- **Standards notes:** images pinned by digest downstream (D7).
- **Depends on:** 2.2. **Blocks:** 3.x (something to attack), 3.3 (flags).
- **Done when:** the reference range builds reproducibly with correct planted
  flags and a working cache.

#### Step 2.6 — Snapshot / restore / deterministic reset  **[v1]**
- **Goal:** Reset a range to a known state cheaply, for repeat runs and A/B arms.
- **Scope:** Implement `snapshot`/`restore` for the Docker backend:
  commit-based snapshots for stateful hosts + a fast "rebuild-from-golden +
  state-overlay" reset path; guarantee that `restore` yields a byte-identical
  starting state for scoring purposes; idempotent and parallel-safe. Wire a
  `range reset` capability used by A/B (6.2) and parallel runs (7.x).
- **Out of scope:** VM snapshots (future backend).
- **Implementation:** prefer rebuild-from-golden (cheap, deterministic) over docker
  commit where possible; snapshots store only divergent state. Reset re-seeds the
  RNG-derived artifacts identically. Concurrency-safe via per-handle locks.
- **Contracts produced:** reliable `snapshot`/`restore`/reset semantics relied on
  by A/B + parallel runs.
- **Testing:** docker integration: snapshot → mutate → restore → state matches;
  10× reset yields identical flag set + topology; parallel resets don't interfere.
- **Standards notes:** "deterministic starting state" is a tested guarantee, not a
  hope.
- **Depends on:** 2.2, 2.5. **Blocks:** 6.2, 7.x (efficient repeats).
- **Done when:** repeated runs start from a verified-identical state.

---

### Epic 3 — Inspect integration & single-agent execution

#### Step 3.1 — Inspect bridge: scenario → Task + Range SandboxEnvironment  **[MVP]**
- **Goal:** Make a Range scenario runnable by Inspect, with tool calls executing
  inside the provisioned range.
- **Scope:** `inspect_bridge/task.py`: map a `Scenario` → an Inspect `Task` with a
  `Dataset`/`Sample` carrying objective + milestone metadata. `inspect_bridge/
  sandbox.py`: a custom Inspect **`SandboxEnvironment`** implementation backed by
  the Range `Backend` — Inspect's `exec`/`read_file`/`write_file` route to
  `Backend.exec`/`copy_out`/`copy_in` against the attacker host; sandbox lifecycle
  hooks call `provision`/`teardown`. Register the sandbox provider with Inspect.
- **Out of scope:** the agent loop/tools (3.2), scoring (3.3), multi-agent (5.x).
- **Implementation:** follow Inspect's `SandboxEnvironment` ABC exactly so the rest
  of Inspect's machinery (solvers, transcripts, model providers, compaction) works
  unmodified. The sandbox targets the host whose `role=entry` by default; multi-host
  exec (choosing a host) is exposed via a tool in 3.2. Provision happens in the
  sandbox `task_init`/sample setup; teardown in cleanup (guaranteed via finalizer).
- **Contracts produced:** `scenario_to_task(scenario)`; the `RangeSandbox` provider
  — the load-bearing Inspect integration.
- **Testing:** with the **fake backend**: an Inspect eval runs end-to-end with a
  stub solver that execs one command and reads a flag; teardown always fires.
  `@pytest.mark.docker`: same against a real 1-host range.
- **Standards notes:** conform to Inspect's interface precisely; pin the Inspect
  version and document the ABC surface we depend on (ADR).
- **Depends on:** 1.2, 2.1 (fake) / 2.2 (docker). **Blocks:** 3.2, 3.3, 3.4, all
  agent/orchestrator work.
- **Done when:** `inspect eval` drives a Range scenario and tool calls land inside
  the range.

#### Step 3.2 — Attacker agent: ReAct, toolbox, compaction  **[MVP]**
- **Goal:** A real attacker agent that autonomously works a range.
- **Scope:** `agents/attacker.py`: a ReAct solver (reason → act → observe) using
  Inspect's agent/tool primitives; `agents/tools.py`: tools = `bash`, `python`,
  and `run_on(host_id, cmd)` (multi-host exec through the sandbox), plus
  `submit_flag`; `agents/compaction.py`: context compaction at ~80% window
  (summarize-and-continue, retaining credentials/topology/progress), mirroring the
  approach used in published range work. Configurable model + token budget.
- **Out of scope:** defender (5.2), users (5.3), policy engine (5.4).
- **Implementation:** the agent is model-agnostic (any Inspect-supported provider).
  Tools emit structured tool-call events (consumed by 4.3). Compaction resets are
  recorded as trace events. Token budget enforced; on budget exhaustion the run
  ends cleanly with a partial result. Scaffolding kept minimal/reproducible
  (per published practice) — fancy scaffolds are a future experiment.
- **Contracts produced:** a reusable agent role + toolbox the orchestrator (5.x)
  instantiates for N roles.
- **Testing:** fake backend: agent solves a scripted 2-step toy range
  deterministically (stub/mock model returning canned tool calls); compaction
  triggers and preserves required facts; budget exhaustion ends gracefully.
- **Standards notes:** keep the agent stateless across runs; all state in the
  Inspect store/trace.
- **Depends on:** 3.1. **Blocks:** 3.3, 3.4, 5.x.
- **Done when:** the attacker autonomously progresses a range and emits clean
  tool-call events.

#### Step 3.3 — Flag/milestone scorer + run result model  **[MVP]**
- **Goal:** Turn a run into a scored result against milestones.
- **Scope:** `scoring/flags.py` (detect submitted/observed flags),
  `scoring/milestones.py` (apply sequential vs independent credit per the spec's
  `Scoring`), `scoring/result.py` (`RunResult{run_id, scenario_id, model,
  milestones_completed, steps_completed, max_milestone, flags, tokens, cost,
  wall_time, status}`). Implement as an Inspect **scorer** so it plugs into the
  eval, reading the same flag-generation function as 2.5.
- **Out of scope:** OpsEc scoring (6.3); aggregation across runs (7.3).
- **Implementation:** sequential credit: observing flag N credits all prerequisite
  milestones (matches TLO-style chains); independent: only directly observed.
  Flags matched against the deterministic per-scenario flag set. `RunResult` is a
  pydantic model persisted to the trace store (4.2).
- **Contracts produced:** `RunResult` — the unit every report aggregates.
- **Testing:** unit: sequential vs independent credit on a known chain; partial
  runs scored correctly; flag spoofing (submitting a wrong flag) not credited.
  Integration with 3.2 on the fake backend.
- **Standards notes:** scoring is pure given (trace, spec) — no side effects.
- **Depends on:** 1.3, 2.5, 3.2. **Blocks:** 3.4, 7.3.
- **Done when:** a finished run yields a correct `RunResult`.

#### Step 3.4 — End-to-end single-agent run: `range run`  **[MVP]**
- **Goal:** The linchpin command that ties provision → execute → capture → score →
  teardown into one reproducible run. **This is the heart of the demo.**
- **Scope:** `run/single.py`: orchestrate one run — resolve+validate spec, build
  images (2.5), provision (2.x), run the Inspect attacker eval (3.1/3.2), capture
  the model trace (4.3) and host telemetry (4.4) into the unified store (4.2),
  score (3.3), persist `RunResult`, teardown (always), emit a one-run summary.
  `cli`: `range run <scenario> --model <m> [--seed N] [--budget T]
  [--backend docker|fake] [--keep]`.
- **Out of scope:** parallelism / N runs (7.x), A/B (6.x), multi-agent (5.x).
- **Implementation:** strict ordering with a `try/finally` guaranteeing teardown
  (unless `--keep`). All correlation IDs threaded. Cost (tokens + wall time +
  per-host seconds) recorded. Exit code reflects run status; the summary prints
  milestones reached + flags + cost + a pointer to the run's trace.
- **Contracts produced:** the canonical single-run pipeline reused by the
  controller (7.1) and A/B (6.2).
- **Testing:** fake backend e2e (`tests/e2e`): `range run` on a toy scenario →
  `RunResult` + a queryable trace. `@pytest.mark.docker`: same on a 2-host range.
- **Standards notes:** the run is the transaction; partial failures still tear down
  and still persist a (failed) `RunResult`.
- **Depends on:** 2.x, 3.1–3.3, 4.1–4.4. **Blocks:** 6.x, 7.x, 8.4.
- **Done when:** one command runs a real range attack and produces a scored,
  traced, torn-down result.

---

### Epic 4 — Unified trace layer

#### Step 4.1 — Trace schema & event model  **[MVP]**
- **Goal:** One schema for every event, on one timeline, joinable by correlation
  IDs.
- **Scope:** `trace/schema.py`: a discriminated-union event model —
  `ModelEvent{reasoning|tool_call|tool_result|compaction|token_usage}`,
  `HostEvent{process|auth|file|edr_alert}`,
  `NetworkEvent{flow|dns|http|pcap_ref}`, `LifecycleEvent{provision|ready|
  teardown|snapshot}`, `ScoreEvent{flag|milestone}`. Every event carries
  `CorrelationIds` + `(wall, step_seq, source_seq)` + `source`. A matching
  **Parquet schema** + a stable on-disk layout
  (`s3://…/run_id=…/source=…/part-*.parquet`).
- **Out of scope:** writing/reading (4.2), the capturers (4.3–4.5).
- **Implementation:** pydantic models ↔ Arrow/Parquet via an explicit mapping
  (`pyarrow`). **Schema is versioned** (`schema_version` on every event) so the
  ClickHouse/Kafka migration (future) is a backfill, not a break. Events are
  append-only and immutable.
- **Contracts produced:** the event union + Parquet schema — every capturer emits
  these; every reader consumes them.
- **Testing:** unit: every event type serializes→Parquet→deserializes losslessly
  (hypothesis round-trip); schema-version present; ordering key total + stable.
- **Standards notes:** this schema is an API — additive evolution only;
  `schema_version` bumps documented.
- **Depends on:** 0.2. **Blocks:** 4.2–4.6, scoring/report.
- **Done when:** all event types round-trip through Parquet losslessly.

#### Step 4.2 — Trace store: writer, Parquet events, Postgres index  **[MVP]**
- **Goal:** Durable, append-only event storage + a queryable run index.
- **Scope:** `trace/store.py`: a `TraceStore` interface +
  `ParquetPostgresStore` impl — buffered Arrow writers flushing partitioned
  Parquet to S3 (or local/MinIO via `s3fs`); a Postgres schema (`runs`,
  `scenarios`, `events_index`(run_id, source, time range, counts, parquet paths),
  `run_results`) via `alembic` migrations; an `append(events)` API + a
  `get_run`/`list_runs` API; `RunResult` persistence.
- **Out of scope:** DuckDB query/replay (4.6); ClickHouse (future).
- **Implementation:** writers batch by `(run_id, source)`; flush on size/time;
  exactly-once-ish via idempotent part naming. Postgres holds *metadata + pointers*
  (cheap to query, scales the index); bulky events live in Parquet (cheap to
  store). `TraceStore` is injected everywhere (D5/D8) so ClickHouse is a drop-in
  later.
- **Contracts produced:** `TraceStore` (`append`, `get_run`, `list_runs`,
  `save_result`) — the single seam for all persistence; the Postgres schema.
- **Testing:** `@pytest.mark.postgres` + local Parquet: append N events, query the
  index, read parts back; concurrent appends from multiple sources don't corrupt;
  migrations up/down clean. Unit: buffering/flush logic with a fake filesystem.
- **Standards notes:** append-only; never mutate a written part.
- **Depends on:** 4.1. **Blocks:** 4.3–4.6, 3.4, 7.3.
- **Done when:** events persist and the run index is queryable; ClickHouse could
  replace the impl without touching callers.

#### Step 4.3 — Model-trace capture from Inspect  **[MVP]**
- **Goal:** Turn Inspect's transcript/events into unified `ModelEvent`s.
- **Scope:** `trace/model_capture.py`: subscribe to Inspect's transcript/event
  stream (or post-process the eval log) → emit `ModelEvent`s (reasoning, each tool
  call + result, compaction boundaries, per-call token usage) with correct
  `agent_id`/`step_seq` into the `TraceStore`.
- **Out of scope:** host (4.4) / network (4.5) capture.
- **Implementation:** prefer Inspect's live event hooks for streaming; fall back to
  parsing the `.eval` log if hooks are insufficient (documented either way). Map
  Inspect tool-call IDs → `step_seq`. Token usage feeds cost (§8).
- **Contracts produced:** model events present on the timeline for every run.
- **Testing:** fake backend: run the attacker, assert the emitted `ModelEvent`s
  match the (mocked) model's tool calls 1:1, with monotonic `step_seq` and token
  totals.
- **Standards notes:** capture must not perturb the run (read-only on Inspect).
- **Depends on:** 3.2, 4.2. **Blocks:** 3.4, replay/report.
- **Done when:** every agent action appears as a correlated `ModelEvent`.

#### Step 4.4 — Host telemetry capture  **[MVP]**
- **Goal:** Record what actually happened on each host — the other half of "one
  timeline."
- **Scope:** `trace/host_capture.py` + `telemetry/host_collector`: a lightweight
  per-host collector (sidecar or in-image agent) capturing process exec, auth
  events, and file changes on Linux hosts; ship to the control plane; normalize →
  `HostEvent`s in the `TraceStore`. A simple, dependency-light collector (e.g.
  tail `/var/log/auth.log` + a `fanotify`/`auditd`-lite process/file watcher, or a
  vendored minimal eBPF/`execsnoop`-style tracer) chosen for container
  compatibility under gVisor.
- **Out of scope:** real EDR/Defender (future Windows/VM backend) — v1 emits
  `edr_alert` events only from a *simulated* Linux EDR rule set if the scenario
  defines one.
- **Implementation:** collector writes NDJSON to a host-local path mounted/streamed
  to the collector service; events tagged with `host_id`. Must work under gVisor
  (test the chosen mechanism early; fall back to log-tail + a ptrace/exec wrapper
  if kernel tracing is constrained). Correlate to `step_seq` by wall-clock + run
  context.
- **Contracts produced:** host events on the timeline; the collector contract for
  future richer sensors.
- **Testing:** docker integration: a known command on a host produces the expected
  process+file events; auth attempt produces an auth event; events land in the
  store with correct `host_id`.
- **Standards notes:** collectors are *in-range* (untrusted side); they only ship
  data out, never accept commands in.
- **Depends on:** 2.2, 2.4, 4.2. **Blocks:** 3.4 (full unified trace), 6.3 (OpsEc).
- **Done when:** model + host events appear interleaved on one replayable timeline.

#### Step 4.5 — Network telemetry capture  **[v1]**
- **Goal:** Capture inter-host traffic — flows, DNS, HTTP, PCAP references.
- **Scope:** `trace/net_capture.py` + a capture point on the network fabric (a tap
  container or pcap on the router bridges): per-flow records, DNS queries, HTTP
  metadata, and on-demand PCAP slices stored as `pcap_ref` (path into Parquet/S3
  blob store) → `NetworkEvent`s.
- **Out of scope:** deep packet inspection / decryption (future).
- **Implementation:** `tcpdump`/`pyshark` or an eBPF flow tracer on the router;
  rotate PCAPs per run; store summaries inline + raw PCAP as referenced blobs to
  keep the event stream light. Correlate flows to hosts via the IP map from 2.3.
- **Contracts produced:** network events + PCAP references on the timeline.
- **Testing:** docker integration: a cross-host connection yields a flow + DNS
  event; PCAP slice retrievable; IPs resolve to `host_id`s.
- **Standards notes:** PCAP volume is bounded/rotated; never unbounded capture.
- **Depends on:** 2.3, 4.2. **Blocks:** richer OpsEc, forensic replay.
- **Done when:** network activity is correlated on the same timeline as model+host.

#### Step 4.6 — Trace query (DuckDB) + replay + `range trace`  **[MVP]**
- **Goal:** Read the timeline back — for humans, scoring, and reports.
- **Scope:** `trace/query.py` (DuckDB over the Parquet partitions + Postgres
  index): typed query helpers (events for a run, by source, by time/step range,
  joins); `trace/replay.py` (reconstruct a run as a single ordered timeline of
  typed events); `range trace <run_id> [--source …] [--follow] [--format
  table|json|timeline]` CLI rendering the interleaved model+host(+net) story.
- **Out of scope:** dashboards/UI (future); ML analytics (future).
- **Implementation:** DuckDB attaches the Parquet glob + reads Postgres for run
  scoping; queries are parameterized + typed. Replay yields a deterministic
  ordering via the §8 key. The `timeline` renderer is the demo's "watch the agent
  work" view.
- **Contracts produced:** the query/replay API used by reports (7.3) and the demo.
- **Testing:** integration: after a run, `range trace` reconstructs the full
  ordered timeline; queries by source/step return correct slices; replay ordering
  is deterministic across repeated calls.
- **Standards notes:** queries are read-only; no query mutates state.
- **Depends on:** 4.2 (and benefits from 4.3/4.4/4.5). **Blocks:** 7.3, demo.
- **Done when:** a run can be replayed as one coherent, correctly-ordered timeline.

---

### Epic 5 — Multi-agent orchestration

#### Step 5.1 — Orchestrator core: roles, scheduling, wiring  **[v1]**
- **Goal:** Run N agent roles in one range, each wired to its host, under a
  defined turn/scheduling model.
- **Scope:** `orchestrator/core.py` (instantiate roles from the scenario, manage
  their lifecycle, route each role's tool calls to its assigned host via the
  Inspect sandbox / backend); `orchestrator/scheduler.py` (turn model:
  `parallel` (roles act concurrently) or `round_robin` (deterministic turns) or
  `event_driven`; turn budgets; barrier/step synchronization). Each role is an
  agent instance (3.2 attacker, 5.2 defender, 5.3 users) with its own model,
  toolbox, trace `agent_id`.
- **Out of scope:** the defender/users themselves (5.2/5.3); policy mediation
  (5.4); A/B (6.x).
- **Implementation:** built on Inspect's agent/solver primitives but coordinating
  *multiple* agents over *one* provisioned range — the capability Inspect lacks
  natively. `asyncio` task per role; the scheduler enforces the turn model and a
  global step clock so the unified trace stays coherent across roles. Clean
  cancellation/teardown of all roles.
- **Contracts produced:** the multi-agent run loop reused by A/B + the controller.
- **Testing:** fake backend: 2 roles (attacker + a no-op defender) run under both
  `parallel` and `round_robin`; step clock stays monotonic across roles; cancel
  tears down all roles.
- **Standards notes:** the global step clock is the ordering authority across
  agents (§8).
- **Depends on:** 3.1, 3.2. **Blocks:** 5.2–5.4, 6.x.
- **Done when:** multiple agents act in one range with a coherent shared timeline.

#### Step 5.2 — Defender agent role + defender toolbox  **[v1]**
- **Goal:** An AI defender that can observe and respond — enabling adversarial
  evaluation.
- **Scope:** `agents/defender.py` (a role that reads alerts/telemetry and acts);
  defender tools in `agents/tools.py`: `read_alerts`, `inspect_host`,
  `block_ip(host_id|ip)`, `kill_process(host_id, pid)`, `isolate_host(host_id)`,
  applied through backend/network primitives (2.3 firewall, 2.2 exec). The
  defender consumes the live host/network telemetry (4.4/4.5) as its sensorium.
- **Out of scope:** OpsEc scoring (6.3); learned defenders (future).
- **Implementation:** defender actions mutate the running range (insert firewall
  rule, kill a PID) via the backend; each action is a trace event so attacker vs
  defender interplay is fully recorded. Response actions are rate-limited/gated by
  the policy engine (5.4).
- **Contracts produced:** the defender role + response-action toolbox.
- **Testing:** fake backend: defender `block_ip` actually severs a flow the
  attacker depends on (verified via trace); kill/isolate reflected in host state.
- **Standards notes:** defender actions are real environment mutations, recorded as
  events.
- **Depends on:** 5.1, 4.4 (sensorium), 2.3 (response levers). **Blocks:** 6.x.
- **Done when:** a defender meaningfully reacts to an attacker within a run.

#### Step 5.3 — Neutral / user simulation  **[v1]**
- **Goal:** Realistic background activity so "normal" has a baseline (the thing
  anomaly detection needs).
- **Scope:** `agents/users.py`: scripted and/or lightweight-model-driven "user"
  roles generating benign traffic/process/auth activity (logins, file access, web
  requests) per a configurable profile in the scenario; emits the same host/network
  telemetry as real activity.
- **Out of scope:** high-fidelity human behavior modeling (future).
- **Implementation:** profiles are declarative (rates, action mixes, schedules);
  scripted users are deterministic under seed; optional model-driven variation.
  Activity is tagged (role=user) so analysis can separate signal from baseline.
- **Contracts produced:** baseline-traffic generation feeding OpsEc/anomaly work.
- **Testing:** fake/docker: a user profile produces the expected event mix at
  ~configured rates; deterministic under seed.
- **Standards notes:** baseline activity is first-class telemetry, not noise to
  discard.
- **Depends on:** 5.1, 4.4. **Blocks:** 6.3 (baseline for detection metrics).
- **Done when:** ranges can run with realistic benign background activity.

#### Step 5.4 — Inter-agent policy engine  **[v1]**
- **Goal:** Mediate what agents can see and do — visibility, rate, gating, budgets.
- **Scope:** `orchestrator/policy.py`: a policy layer enforcing inter-agent
  visibility (can the defender see the attacker's host directly?), per-agent
  action rate limits, action gating (some actions require a turn/budget), and
  global turn budgets; configured in the scenario's `orchestration` block.
- **Out of scope:** cryptographic isolation between agents (future).
- **Implementation:** policies are declarative rules evaluated at action time;
  violations are denied + recorded as events (not crashes). Sits between the
  agents and the backend/sandbox so it governs every action uniformly.
- **Contracts produced:** uniform action mediation across all roles.
- **Testing:** fake backend: a visibility rule hides a host from the defender; a
  rate limit throttles an agent; a denied action is recorded, not fatal.
- **Standards notes:** deny-and-record, never crash, on policy violation.
- **Depends on:** 5.1. **Blocks:** realistic multi-agent scenarios.
- **Done when:** agent capabilities are governed by declarative policy.

---

### Epic 6 — Defense A/B & OpsEc scoring

#### Step 6.1 — Defense configuration & insertion  **[v1]**
- **Goal:** Make defenses a toggle, so "with vs without" is a config change.
- **Scope:** finalize the scenario `defenses` block (EDR/SIEM rule sets, network
  segmentation policy, an optional defender-agent toggle, host hardening levels)
  and an applier that materializes a given defense configuration into the
  provisioned range at provision time (rules loaded, segmentation applied,
  defender enabled/disabled).
- **Out of scope:** the A/B harness (6.2); scoring (6.3).
- **Implementation:** a defense config is a named, hashable bundle; provisioning
  takes `(scenario, defense_config)` so two arms differ *only* by defenses.
  Simulated Linux EDR rules (from 4.4's `edr_alert` mechanism) are data-driven.
- **Contracts produced:** `DefenseConfig` + the applier — consumed by A/B.
- **Testing:** docker: enabling a SIEM rule produces alerts for a triggering
  action; segmentation policy blocks a path that's open without it; disabling
  yields the baseline.
- **Standards notes:** arms differ only by `DefenseConfig` (provable via the
  scenario+defense hash).
- **Depends on:** 2.3, 4.4, 5.2. **Blocks:** 6.2, 6.3.
- **Done when:** the same range provisions with different, verifiable defense
  postures.

#### Step 6.2 — A/B run harness  **[v1]**
- **Goal:** Run identical environments side-by-side across defense arms.
- **Scope:** `run/ab.py`: given `(scenario, model, [defense_config…], N)`, run N
  attempts per arm on environments identical except for `DefenseConfig`
  (leveraging 2.6 reset for identical starting state), capture comparable traces
  tagged by `arm_id`, and persist arm-tagged results.
- **Out of scope:** OpsEc metrics/diff (6.3); large-scale scheduling (7.x, which
  this composes with).
- **Implementation:** uses the single-run pipeline (3.4) per attempt with `arm_id`
  threaded through correlation IDs; reuses snapshots/golden images so arms are
  truly comparable; parallelism delegated to the run controller (7.x).
- **Contracts produced:** arm-tagged runs ready for comparative scoring.
- **Testing:** fake/docker: two arms (defense on/off) over N=3 produce arm-tagged
  results from identical starting states.
- **Standards notes:** "identical except defenses" is a tested invariant.
- **Depends on:** 3.4, 6.1, 2.6. **Blocks:** 6.3.
- **Done when:** A/B arms run and are comparably traced.

#### Step 6.3 — OpsEc scoring & trace diff  **[v1]**
- **Goal:** Quantify detection/evasion and compare arms — the metric the industry
  lacks.
- **Scope:** `scoring/opsec.py`: alerts-per-step, time-to-first-detection,
  attacker-progress-vs-detection curves, and progress-with-vs-without each defense
  — computed against the baseline from user simulation (5.3) where present; a
  trace-diff producing a side-by-side arm comparison; an A/B report (extends 7.3).
- **Out of scope:** learned anomaly baselines (future analytics).
- **Implementation:** OpsEc metrics derive from `edr_alert`/network events joined
  to `step_seq`; baseline (5.3) gives "normal" to measure anomalies against. Diff
  aligns arms by milestone for fair comparison. Clearly label early-stage metrics
  as such (matching the field's own caveats).
- **Contracts produced:** OpsEc metrics + arm-diff consumed by reports.
- **Testing:** synthetic traces with known alert patterns yield expected
  alerts/step + TTD; diff highlights the arm difference correctly.
- **Standards notes:** metrics are reproducible functions of (traces, spec,
  baseline).
- **Depends on:** 6.2, 4.4, 5.3. **Blocks:** comparative reporting.
- **Done when:** an A/B run yields OpsEc metrics + a side-by-side arm report.

---

### Epic 7 — Parallel run controller & reporting

#### Step 7.1 — Run controller  **[v1]**
- **Goal:** Submit a campaign and have it scheduled, tracked, resumable, and
  costed.
- **Scope:** `run/controller.py`: accept `(scenario, model, defense_config?, N,
  seed_strategy)`; expand into a run plan; schedule runs (delegating execution to
  3.4 / 6.2); track per-run lifecycle/state in Postgres; retries + **resume** of an
  interrupted campaign; aggregate token + infra cost.
- **Out of scope:** the worker pool/quotas (7.2); report rendering (7.3).
- **Implementation:** a `Campaign` record + `Run` rows in Postgres drive
  idempotent resume (re-derive what's done from persisted results). Seed strategy
  controls run-to-run variance studies. Backpressure handed to 7.2.
- **Contracts produced:** the campaign abstraction + persisted plan/state.
- **Testing:** fake backend: a 5-run campaign completes; killing mid-campaign and
  re-running resumes only the missing runs; cost aggregates correctly.
- **Standards notes:** campaigns are resumable transactions; never double-run a
  completed unit.
- **Depends on:** 3.4 (and 6.2 for A/B campaigns). **Blocks:** 7.2, 7.3.
- **Done when:** a multi-run campaign runs, resumes, and reports cost.

#### Step 7.2 — Concurrency & resource management  **[v1]**
- **Goal:** Run many ranges at once without melting the host or leaking resources.
- **Scope:** `run/pool.py`: an async worker pool with configurable max-parallel
  runs; per-resource quotas (CPU/mem/containers); backpressure when saturated;
  guaranteed cleanup-on-failure (no orphaned containers/networks even under crash);
  graceful drain on shutdown.
- **Out of scope:** distributed/multi-node scheduling (future cloud backend).
- **Implementation:** a semaphore-bounded pool; quota accounting before
  provisioning; a reaper that sweeps orphaned labeled resources (2.2) on
  start/shutdown; cooperative cancellation propagates to teardown.
- **Contracts produced:** safe bounded concurrency for campaigns.
- **Testing:** docker: 10 concurrent toy runs respect max-parallel; an induced
  mid-run crash leaves zero orphaned resources after the reaper; drain finishes
  in-flight runs.
- **Standards notes:** **no resource leaks** is a hard, tested guarantee.
- **Depends on:** 7.1, 2.2. **Blocks:** scaled campaigns.
- **Done when:** large campaigns run bounded, clean, and resumable.

#### Step 7.3 — Results aggregation & report generation  **[v1]** (single-run summary is **[MVP]**)
- **Goal:** Turn runs into decisions — stats, milestone matrices, shareable
  reports.
- **Scope:** `report/aggregate.py` (per-run + aggregate stats: avg/max steps,
  variance, success rate, milestone-completion matrix, cost) and `report/render.py`
  (Markdown + JSON reports) and `report/matrix_svg.py` (a milestone × runs/models
  completion-matrix SVG). The **single-run summary** (used by `range run`) is MVP;
  the aggregate/A/B/matrix reporting is v1.
- **Out of scope:** interactive dashboards (future).
- **Implementation:** aggregation reads the trace store (4.6) + `RunResult`s;
  matrices mirror published TLO-style step/milestone matrices; SVG generated with a
  small templating helper (exportable, self-contained). Reports embed cost +
  variance prominently (the metrics buyers care about).
- **Contracts produced:** the report artifacts shareable with stakeholders.
- **Testing:** unit: aggregation math on known `RunResult` sets; SVG renders for a
  matrix fixture (valid SVG, expected cells); markdown/json snapshots.
- **Standards notes:** reports are deterministic functions of stored results.
- **Depends on:** 3.3, 4.6 (and 6.3 for A/B reports). **Blocks:** 8.4.
- **Done when:** a campaign yields a clear Markdown/JSON report + milestone-matrix
  SVG.

---

### Epic 8 — Productionization & operability

#### Step 8.1 — CLI consolidation & UX  **[v1]** (lean `validate`/`run`/`trace` are **[MVP]**)
- **Goal:** One coherent, documented `range` CLI.
- **Scope:** consolidate subcommands — `validate`, `run`, `campaign`
  (controller), `ab`, `trace`, `report`, `images`, `reset` — under a Typer app
  with consistent flags, config-profile selection, `--json` output everywhere,
  good help, and shell completion. (The MVP needs only `validate`, `run`,
  `trace`.)
- **Out of scope:** a web UI (future).
- **Implementation:** thin CLI over the `run`/`report`/`spec` libraries (no logic
  in the CLI). Consistent exit codes mapped from `RangeError.code`. Profiles select
  backend/store/log settings.
- **Contracts produced:** the operator interface for v1.
- **Testing:** `typer.testing` coverage of each command's happy path + error exit
  codes.
- **Standards notes:** CLI is presentation only; all behavior is in libraries.
- **Depends on:** the features each command fronts. **Blocks:** 8.4, launch.
- **Done when:** every v1 capability is reachable via a documented command.

#### Step 8.2 — Range self-observability  **[v1]**
- **Goal:** Operate Range itself in production.
- **Scope:** structured logs (already via §7) enriched with run context;
  **Prometheus metrics** (`runs_total`, `provision_duration_seconds`,
  `backend_errors_total`, `queue_depth`, `tokens_total`, `cost_usd_total`); health
  endpoints; a per-run **audit log** distinct from in-range telemetry.
- **Out of scope:** in-range telemetry (that's Epic 4 — different thing).
- **Implementation:** a metrics registry exposed via an optional HTTP endpoint;
  metrics emitted from controller/pool/backend; audit log persisted to Postgres.
- **Contracts produced:** ops signals for running Range as a service.
- **Testing:** unit: metrics increment on simulated events; health reflects
  store/backend reachability; audit entries persisted.
- **Standards notes:** keep Range's own observability separate from captured
  range telemetry.
- **Depends on:** 7.1/7.2, 4.2. **Blocks:** production deploy.
- **Done when:** Range exposes health + metrics + an audit trail.

#### Step 8.3 — Packaging, containerization & deploy  **[v1]**
- **Goal:** Ship Range as a deployable artifact + a one-command local full stack.
- **Scope:** a control-plane container image (digest-pinned base); a
  `docker-compose` bringing up Range + Postgres + MinIO (S3) for local/dev; a
  sketched Kubernetes/Helm manifest for the control plane (workers, Postgres, S3);
  secrets via env/secret store; a documented bootstrap (`migrate`, configure
  profiles).
- **Out of scope:** managed cloud provisioner backends (future); autoscaling.
- **Implementation:** the control plane and workers share the image; compose wires
  the local store; Helm values expose store/backend/secret config. Note the
  Docker-in-Docker / runsc requirements for nodes that provision ranges.
- **Contracts produced:** the deployable unit + local stack used by demos/tests.
- **Testing:** CI builds the image; `docker compose up` + the E2E (8.4) runs
  against the composed stack.
- **Standards notes:** images digest-pinned; secrets never baked in.
- **Depends on:** 8.1, 8.2, 4.2. **Blocks:** launch, 8.4 (compose-based E2E).
- **Done when:** `docker compose up` yields a working Range; image builds in CI.

#### Step 8.4 — Docs, reference range & golden-path E2E  **[MVP]**
- **Goal:** The thing you actually demo + the test that proves the whole loop.
- **Scope:** a complete **"Mini-Enterprise"** reference scenario in
  `examples/scenarios/` (≥2 subnets, ~5–6 Linux hosts: entry, web app, internal
  file server, workstation, a "crown-jewel" target DB; composed from fragments;
  a ~6–8-step milestone chain with planted flags); a tutorial (`README` +
  `docs/tutorial.md`) walking validate → run → trace → report; a **golden-path
  E2E test** (`tests/e2e`) running the full pipeline on the fake backend in CI and
  on Docker locally; a short demo script for showing Irregular.
- **Out of scope:** multiple reference ranges (future library expansion).
- **Implementation:** the reference range is the canonical artifact every other
  step is validated against; the E2E asserts a scored `RunResult` + a replayable
  unified (model+host) trace + a generated report. The demo script narrates "watch
  the agent work the timeline."
- **Contracts produced:** the reference range + the E2E gate + the demo.
- **Testing:** the E2E *is* the test (fake-backend in CI; `@pytest.mark.docker`
  locally); tutorial commands verified.
- **Standards notes:** the reference range tracks every spec/scoring change (it's
  the living integration fixture).
- **Depends on:** essentially all MVP steps. **Blocks:** launch / demo.
- **Done when:** a newcomer can `validate → run → trace → report` the
  Mini-Enterprise range end-to-end, and CI proves it.

---

## 10. The MVP cut — the naive demo

**Goal of the demo:** show Irregular (and other labs) a *real* multi-host network
simulation, provisioned from a declarative config, where a Claude/GPT attacker
agent autonomously works the network, with **model + host activity captured on one
replayable timeline** and scored against milestones — running at container/gVisor
fidelity, Linux-only, with the architecture visibly built to extend to VM fidelity,
AI defenders, and parallel A/B (which you say you're building next).

**MVP step set (21 steps):**

```
Epic 0:  0.1  0.2  0.3                       (0.3 = Terraform/OCI host)
Epic 1:  1.1  1.2  1.3
Epic 2:  2.1  2.2  2.3  2.4  2.5            (2.6 deferred)
Epic 3:  3.1  3.2  3.3  3.4
Epic 4:  4.1  4.2  4.3  4.4  4.6            (4.5 network telemetry deferred)
Epic 8:  8.4   (+ lean 8.1 validate/run/trace, + single-run summary from 7.3)
```

**Deferred to "remaining features I'm actively building" (the honest pitch):**
2.6 snapshot/reset · 4.5 network telemetry · Epic 5 (defender + users +
policy/orchestrator) · Epic 6 (defense A/B + OpsEc) · Epic 7.1/7.2 (parallel
campaigns at scale) · 8.2 (metrics/audit) · 8.3 (full deploy/Helm).

**Why this is a credible naive demo and not a toy:** it exercises the load-bearing
seams that make the full product real — the provisioner **abstraction** (so VM
fidelity is additive), the **Inspect** integration (so the ecosystem trusts it),
and the **unified trace** (the core differentiator). Everything deferred is an
*addition* behind an interface that already exists, never a rewrite. That is the
story that makes "I'm building the rest" believable.

**Demo script (≈5 minutes):**
1. `range validate examples/scenarios/mini-enterprise.yaml` → topology + milestone
   summary, zero errors.
2. `range run examples/scenarios/mini-enterprise.yaml --model <frontier-model>
   --seed 1` → Range provisions ~6 isolated containers across 2 subnets (gVisor,
   no internet), drops the attacker on the entry host, and the agent works the
   chain autonomously.
3. `range trace <run_id> --format timeline` → the killer view: the agent's
   reasoning and commands **interleaved with the host events they caused**
   (processes spawned, auth attempts, files touched), on one clock.
4. The run summary: milestones reached, flags captured, tokens + cost, status.
5. Point at `range-architecture-v1.svg`: "solid green is what you just saw; blue is
   v1 in flight; dashed amber — VM/AD fidelity, AI defenders, defense A/B at scale —
   is what I'm building behind the same interfaces."

---

## 11. Critical path & suggested ordering

The hard dependency spine (also in `range-build-map.svg`):

```
0.1 → 0.2 → 0.3                         (0.3 host blocks Docker integration: 2.2+)
      ├─ 1.1 → 1.2 → 1.3
      ├─ 2.1(+fake) → 2.2 → 2.3 → 2.4
      │                └─ 2.5
      └─ 4.1 → 4.2
3.1 (needs 1.2 + 2.1/2.2 + Inspect) → 3.2 → 3.3 (needs 1.3, 2.5) ┐
4.3 (needs 3.2 + 4.2)                                            ├→ 3.4 → 8.4  ← MVP demo
4.4 (needs 2.2/2.4 + 4.2)                                        │
4.6 (needs 4.2)                                                  ┘
— then post-MVP —
5.1 → {5.2, 5.3, 5.4} → 6.1 → 6.2 → 6.3
3.4 → 7.1 → 7.2 ;  {3.3,4.6,6.3} → 7.3
8.1 ← (all features) ;  8.2, 8.3 ← (7.x, 4.2)
```

**Recommended order:** 0.1, 0.2, 0.3 → 1.1, 1.2, 1.3 → 2.1, 2.2, 2.3, 2.4, 2.5 →
4.1, 4.2 → 3.1, 3.2, 3.3 → 4.3, 4.4 → 4.6 → 3.4 → 8.4 **(MVP done — demo here)** →
2.6 → 4.5 → 5.1, 5.2, 5.3, 5.4 → 6.1, 6.2, 6.3 → 7.1, 7.2, 7.3 → 8.1, 8.2, 8.3.

**Highest-risk steps (review hardest):** **2.1** (the backend interface — the
seam the whole product pivots on), **3.1** (the Inspect `SandboxEnvironment`
bridge — conform exactly), **4.4** (host telemetry under gVisor — validate the
capture mechanism *early*; if kernel tracing is constrained under runsc, fall back
to log-tail + an exec wrapper, decided in 4.4's spike).

---

## 12. Testing strategy

- **Unit (fast, no infra):** every pure module — `spec`, `scoring`, `trace/schema`,
  `provision/base` + `fake`, `report` math. The **fake backend (2.1)** lets the
  entire run pipeline (orchestrator, agents via mock model, scoring, trace) be
  tested with zero Docker.
- **Property tests (hypothesis):** spec round-trip + `scenario_id` invariance;
  fragment-merge determinism; trace event Parquet round-trip; scoring credit
  monotonicity.
- **Integration (gated by markers):** `@pytest.mark.docker` (backend, network,
  gVisor, images, host/net capture), `@pytest.mark.postgres` (trace store,
  controller state). Skipped automatically where infra/`runsc` is absent, with a
  `runc`-hardened fallback path tested instead.
- **E2E (8.4):** the golden-path pipeline on the **fake backend in CI** (always
  runs) and on **Docker locally / nightly** (full fidelity).
- **CI gates (must pass to merge):** ruff, mypy --strict, import-linter, unit +
  available integration, coverage ≥90% on core. Coverage ratchet only goes up.
- **Determinism tests:** same spec + seed ⇒ identical flags, identical topology,
  identical replay ordering.
- **Leak tests:** post-run/teardown resource sweeps assert zero orphaned
  containers/networks by label (7.2 especially).

---

## 13. Glossary

- **Range (the platform):** this product. **A range:** one provisioned, isolated,
  multi-host environment under test.
- **Scenario / spec:** the declarative description of a range (topology, hosts,
  services, vulns, identities, defenses, milestones, scoring).
- **Backend:** a provisioner implementation behind the `Backend` interface (v1:
  fake, Docker+gVisor; future: Firecracker/libvirt/Proxmox/cloud).
- **Fidelity tier:** how realistically a host is emulated — container (v1) vs
  microVM/VM (future, for real EDR/AD).
- **Inspect / Inspect AI:** UK AISI's open-source eval framework Range builds on
  for agent execution + sandbox protocol.
- **SandboxEnvironment:** Inspect's interface for where tool calls execute; Range
  implements one backed by its provisioner.
- **Agent role:** an attacker/defender/user instance with its own model, toolbox,
  and trace identity.
- **Unified trace:** the single, correlated, time-ordered event stream combining
  model + host + network + lifecycle + score events.
- **Milestone / flag:** a scored checkpoint in the attack chain / the token proving
  a step was reached.
- **OpsEc scoring:** detection/evasion metrics (alerts-per-step,
  time-to-detection, progress-with-vs-without a defense).
- **A/B / arm:** running the same range under different defense configurations to
  compare outcomes.
- **Campaign:** a controller-managed set of N runs (optionally across arms/models).
- **Golden image:** a reproducible, content-addressed, digest-pinned host image
  carrying services/vulns/flags.

---

*End of v1 design. See `RANGE_FUTURE_DEVELOPMENT.md` for everything beyond v1 and
the running improvements backlog.*
