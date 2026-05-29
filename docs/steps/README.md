# Range — Build Steps

One file per build step. Each file is a **self-contained Claude Code session
prompt**: paste it into a fresh session and it has everything needed to land that
step as a single green PR. Steps follow the plan in `docs/RANGE_DESIGN_V1.md` §9.

## How to use

1. **Read `_SHARED_STANDARDS.md` first** (the agent should too — each step links
   it). It holds the rules every step assumes, so the step files don't repeat
   them.
2. Do steps **in dependency order** (see each file's *Dependencies* and §11 of the
   design doc). Within an epic, ascending order is safe.
3. **One step = one PR.** The step is done only when its *Done when* checklist all
   holds and CI is green.
4. Place these files in the repo at `docs/steps/` so the running agent can read
   the shared standards and cross-reference sibling steps.

## Conventions

- **Dependencies are added per-step** — each file lists the libraries it
  introduces. Don't pre-add anything.
- **`[MVP]`** = part of the naive demo (§10). All Epic 0–1 steps are MVP.
- Code-quality bar (DRY/YAGNI/KISS, surgical, skimmable, short-hand comments) is
  in `_SHARED_STANDARDS.md` and applies to every step.

## Status — Epics 0, 1, 2, 3 & 4

| Step | File | Title | Tag |
|------|------|-------|-----|
| 0.1 | `epic-0/0.1-repo-scaffold-tooling-ci.md` | Repository scaffold, tooling, CI | MVP |
| 0.2 | `epic-0/0.2-core-primitives.md` | Core primitives: ids, logging, errors, config, time | MVP |
| 0.3 | `epic-0/0.3-terraform-oci-foundation.md` | Infrastructure foundation: Terraform + OCI host | MVP |
| 1.1 | `epic-1/1.1-scenario-spec-schema-loader.md` | Scenario spec schema + YAML loader | MVP |
| 1.2 | `epic-1/1.2-spec-validation-cli.md` | Spec validation, linting & `range validate` | MVP |
| 1.3 | `epic-1/1.3-milestones-scoring-fragments.md` | Milestones, scoring spec & building-block fragments | MVP |
| 2.1 | `epic-2/2.1-backend-interface-fake.md` | Provisioner interface, lifecycle SM & fake backend | MVP |
| 2.2 | `epic-2/2.2-docker-backend.md` | Docker backend: hosts → containers | MVP |
| 2.3 | `epic-2/2.3-network-fabric.md` | Network fabric: subnets, routing, firewall, egress | MVP |
| 2.4 | `epic-2/2.4-gvisor-hardening.md` | gVisor runtime + isolation hardening | MVP |
| 2.5 | `epic-2/2.5-golden-images-injection.md` | Golden-image build pipeline + vuln/flag injection | MVP |
| 2.6 | `epic-2/2.6-snapshot-reset.md` | Snapshot / restore / deterministic reset | v1 |
| 3.1 | `epic-3/3.1-inspect-bridge.md` | Inspect bridge: scenario → Task + Range SandboxEnvironment | MVP |
| 3.2 | `epic-3/3.2-attacker-agent.md` | Attacker agent: ReAct, toolbox, compaction | MVP |
| 3.3 | `epic-3/3.3-scorer-run-result.md` | Flag/milestone scorer + run result model | MVP |
| 3.4 | `epic-3/3.4-range-run-e2e.md` | End-to-end single-agent run: `range run` | MVP |
| 4.1 | `epic-4/4.1-trace-schema.md` | Trace schema & event model | MVP |
| 4.2 | `epic-4/4.2-trace-store.md` | Trace store: writer, Parquet events, Postgres index | MVP |
| 4.3 | `epic-4/4.3-model-capture.md` | Model-trace capture from Inspect | MVP |
| 4.4 | `epic-4/4.4-host-telemetry.md` | Host telemetry capture | MVP |
| 4.5 | `epic-4/4.5-network-telemetry.md` | Network telemetry capture | v1 |
| 4.6 | `epic-4/4.6-trace-query-replay.md` | Trace query (DuckDB) + replay + `range trace` | MVP |

**Dependency spine:** `0.1 → 0.2 → 0.3 → 1.1 → 1.2 → 1.3`, then
`2.1(+fake) → 2.2 → 2.3 → 2.4`, with `2.2 → 2.5` and `2.2,2.5 → 2.6`, then
`3.1 → 3.2 → 3.3`, with the trace layer `4.1 → 4.2 → {4.3, 4.4, 4.5, 4.6}`.

**⚠️ Epic 3 ↔ Epic 4 interleave (build the trace layer around Epic 3, not strictly
after it).** `4.1 → 4.2` can be built **early** (right after `0.2`/`2.2`), in
parallel with the spec/provisioner. Then: `4.3` needs `3.2`+`4.2`; `4.4` needs
`2.2`/`2.4`+`4.2`; `4.6` needs `4.2`. `3.4` (`range run`) is the join point — it
needs `2.5`, `3.1–3.3`, **and** `4.1–4.4`. Per design doc §11:
`{3.3, 4.3, 4.4, 4.6} → 3.4 → 8.4`. A practical order:
`… 2.2, 4.1, 4.2 … 3.1, 3.2, 4.3, 3.3, 4.4, 4.6 → 3.4`.

The **Terraform/OCI host (0.3)** must exist before any `@pytest.mark.docker`
integration test (2.2+). **Step 4.2 adds the on-host services layer**
(`deploy/compose/` — Postgres) and an optional, gated OCI Object Storage bucket
(Terraform); v1 defaults to block-volume Parquet. Infra grows per-step; see the
"Infrastructure (Terraform)" section in each step file. Epic 3 application steps
and most of Epic 4 add **no** new OCI resource (model-provider egress is open in
0.3; keys via `config`; managed-secrets / managed-Postgres / object-storage are
backlog B-34/B-35/B-36).
