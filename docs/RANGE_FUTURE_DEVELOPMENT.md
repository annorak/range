# Range — Future Development & Improvements Backlog

> This document holds everything **beyond v1**. v1 (see `RANGE_DESIGN_V1.md`) ships
> a real, launchable, container-fidelity, Linux-only, CLI-driven platform. Every
> item here is **additive behind interfaces v1 already defines** — by design,
> almost nothing below is a rewrite.

It has two parts:
- **Part A — Thematic future epics** (the product roadmap, F-A … F-L).
- **Part B — Running improvements backlog** (a concrete, sized, triggerable list,
  including the deferrals v1 itself created).

Each future epic lists steps at a lighter altitude than v1's (goal / what / why /
rough size / depends-on or trigger). Promote any of these to a full v1-style step
spec when you pick it up.

---

## Part A — Thematic future epics

### F-A. Higher-fidelity provisioner backends
*The whole point of v1's `Backend` abstraction (Step 2.1) was to make this purely
additive.*

- **F-A.1 — Firecracker microVM backend.** Implement `Backend` over Firecracker
  for kernel-level fidelity (real kernel behaviors, stronger isolation) on
  bare-metal/nested-virt hosts. Golden images become rootfs + kernel pairs; warm
  pools + snapshot/restore for fast boot. *Size: L. Depends: 2.1, 2.5, 2.6.
  Trigger: when a scenario needs real-kernel fidelity or a partner asks for
  VM-grade isolation.*
- **F-A.2 — libvirt/KVM backend.** General VM backend for full-OS hosts (incl. the
  Windows path in F-B). *Size: M–L. Depends: 2.1. Trigger: Windows/AD work, or
  full-OS services.*
- **F-A.3 — Proxmox backend.** Match the AISI/Inspect Proxmox option for
  high-isolation evaluations and on-prem clusters. *Size: M. Trigger: a partner
  standardized on Proxmox.*
- **F-A.4 — Cloud backends (AWS/GCP).** Provision ranges as cloud VMs/VPCs for
  elastic scale. *Size: L. Depends: 2.1, 7.2. Trigger: campaigns outgrow a single
  host.*
- **F-A.5 — Hybrid scheduler.** Place each host on the cheapest sufficient tier
  *within one range* (containers for stateless, VMs for fidelity); the scenario
  declares per-host fidelity requirements and the scheduler chooses. *Size: M.
  Depends: ≥2 backends. Trigger: mixed-fidelity ranges become common.*

### F-B. Windows / Active Directory fidelity
*Required to reproduce the canonical enterprise scenarios (real AD, real Windows
Defender) — the TLO/SpecterOps class.*

- **F-B.1 — Windows Server images via evaluation editions.** Build Windows host
  images from Microsoft **evaluation editions** (Windows Server eval ≈180-day,
  re-armable; Windows 10/11 Enterprise eval ≈90-day) — **free for non-production
  lab/eval use**, so no per-seat license purchase. *Size: M. Depends: F-A.2 or
  F-A.1. Note: validate current Microsoft eval terms at build time.*
- **F-B.2 — Active Directory topology.** Domain controller + domain-joined hosts,
  realistic (mis)configurations, Kerberos/NTLM, the AD attack surface (the
  bottleneck class in published ranges). *Size: L. Depends: F-B.1.*
- **F-B.3 — Real Windows EDR / Defender integration.** Run real Windows Defender
  (and pluggable EDR) as a true defense for OpsEc/A/B arms. *Size: M. Depends:
  F-B.1, 6.1.*
- **F-B.4 — Self-hosted lab host backend.** A backend targeting a self-managed
  hypervisor host (e.g. an unused Windows PC running Hyper-V, or a Linux box
  running KVM/Firecracker) so Windows+Linux VM ranges can be built **for free** on
  owned hardware before paying for cloud. *Size: M. Depends: F-A.1/F-A.2.*

### F-C. Trace & data-platform evolution
*v1 is Postgres + S3/Parquet + DuckDB behind the `TraceStore` interface (Step 4.2),
deliberately so this is a drop-in.*

- **F-C.1 — ClickHouse analytical store.** Implement `TraceStore` over ClickHouse
  for fast analytical queries over very large event volumes; backfill from Parquet
  (events are append-only + schema-versioned, so it's a migration, not a break).
  *Size: M–L. Depends: 4.1, 4.2. Trigger: query latency on DuckDB/Parquet hurts at
  campaign scale, or analytics (F-D) needs interactive aggregation.*
- **F-C.2 — Kafka (or Redpanda) ingestion.** Put a durable streaming bus in front
  of capture for high-throughput, real-time, multi-run ingest and replayable
  pipelines. *Size: M. Depends: 4.2. Trigger: many concurrent ranges saturate
  direct writes, or live-monitoring (F-E live view) needs streaming.*
- **F-C.3 — Real-time trace streaming.** Live tail of the unified timeline during a
  run (for the web live-view and for human-in-the-loop re-steering). *Size: M.
  Depends: F-C.2.*
- **F-C.4 — OpenTelemetry export.** Emit traces/metrics in OTel so partners can
  pipe Range data into their existing observability stacks. *Size: S–M.*

### F-D. Advanced analytics (the "10k transcripts → conclusions" layer)
*Sits on the unified trace store; v1 ships deterministic stats + matrices, this is
the intelligence layer.*

- **F-D.1 — Transcript clustering & failure-mode taxonomy.** Embed + cluster run
  transcripts; auto-surface recurring failure modes ("model emailed the
  organizers", "looped on tool errors") across thousands of runs. *Size: L.
  Depends: 4.6, ideally F-C.1.*
- **F-D.2 — Behavioral baselining & anomaly detection.** Learn "normal" from
  user-simulation baselines (Step 5.3) and score deviations — directly attacking
  the "anomaly detection has no baseline" gap. *Size: L. Depends: 5.3, 6.3.*
- **F-D.3 — Detection-aware / OpsEc analytics v2.** Robust, baseline-relative
  detection metrics replacing v1's intentionally-early-stage OpsEc. *Size: M.
  Depends: 6.3, F-D.2.*
- **F-D.4 — Capability-trend tracking.** Longitudinal dashboards of model
  performance across releases/ranges (TLO-style trend lines) as a standing
  artifact. *Size: M. Depends: 7.3.*
- **F-D.5 — Mechinterp / activation capture hooks.** Optional capture of model
  internals (where providers allow) as another correlated trace source for
  "inside + outside" analysis. *Size: L. Depends: 4.1, provider access.*

### F-E. Web console / UI
- **F-E.1 — Run + campaign dashboard.** Browse runs/campaigns, results, costs.
  *Size: M. Depends: 4.6, 7.x.*
- **F-E.2 — Live timeline viewer.** Watch the unified model+host+network timeline
  as a run unfolds — the "watch the agent work" experience as a product surface.
  *Size: L. Depends: F-C.3.*
- **F-E.3 — Report browser + scenario editor.** View/share reports; a guided
  scenario/fragment authoring UI with live validation. *Size: L. Depends: 1.x,
  7.3.*

### F-F. SaaS & multi-tenancy
- **F-F.1 — AuthN/Z + orgs + RBAC.** *Size: M.*
- **F-F.2 — Tenant isolation + quotas + billing.** Hard isolation of ranges/data
  per tenant; usage metering + billing. *Size: L. Depends: 7.2, 8.2.*
- **F-F.3 — Enterprise secret management + audit at scale.** KMS/Vault integration,
  full audit. *Size: M. Depends: 8.2.*

### F-G. Scenario ecosystem
- **F-G.1 — Expanded fragment & range library.** Many reusable building blocks +
  several reference ranges (multi-domain AD, CI/CD supply-chain, cloud, OT).
  *Size: ongoing. Depends: 1.3, fidelity backends.*
- **F-G.2 — MITRE ATT&CK mapping.** Tag milestones/steps to ATT&CK techniques for
  standardized coverage reporting. *Size: M.*
- **F-G.3 — Range sharing / marketplace.** Import/export + share community ranges.
  *Size: L. Depends: content-addressed specs (1.1), F-F.*
- **F-G.4 — Partner content integration.** Ingest/standardize ranges authored in
  the style of SpecterOps / Hack The Box content. *Size: M.*

### F-H. Scaling the runner
- **F-H.1 — Distributed multi-node scheduling.** Run campaigns across a fleet
  (beyond a single control host). *Size: L. Depends: 7.1, 7.2, a cloud/K8s
  backend.*
- **F-H.2 — K8s-native execution.** Map runs/ranges onto Kubernetes jobs/pods with
  the K8s sandbox model. *Size: M–L. Depends: F-A.*
- **F-H.3 — Warm pools + snapshot fleets + spot/cost optimization.** Pre-warmed
  environments and cost-aware placement to cut spin-up and $$. *Size: M. Depends:
  2.6, F-A.1.*

### F-I. RL & training-environment export
*Turns Range from a measurement tool into a training-data engine — strategically
adjacent to where the labs and infra companies are spending.*

- **F-I.1 — Gym-style RL environment wrapper.** Expose a range as an RL environment
  (observation/action/reward) over the orchestrator + trace. *Size: L. Depends:
  5.x, 4.x.*
- **F-I.2 — Reward shaping from milestones/OpsEc.** Dense rewards from milestone
  progress and stealth (OpsEc), for training offensive/defensive agents. *Size: M.
  Depends: 3.3, 6.3.*
- **F-I.3 — Training-stack integration.** Hooks for common RL/training
  infrastructure to consume Range environments at scale. *Size: L. Depends: F-I.1,
  F-H.*

### F-J. ICS / OT / digital twins
*The "Cooling Tower" class — physical-process fidelity.*

- **F-J.1 — PLC/HMI simulators + OT protocols.** Simulated industrial controllers
  and HMIs with real OT protocol behavior. *Size: L. Depends: F-A.*
- **F-J.2 — Digital-twin physical-process models.** Model pumps/valves/processes so
  attacks have physical consequences to score. *Size: L. Depends: F-J.1.*

### F-K. Advanced agent capabilities
- **F-K.1 — Custom scaffolds + tool delegation + sub-agents.** Beyond v1's minimal
  ReAct; pluggable expert scaffolds and multi-agent attacker teams. *Size: M.
  Depends: 3.2, 5.1.*
- **F-K.2 — Human-in-the-loop re-steering.** Pause/inject/redirect an agent at
  bottlenecks (a key published threat model) via the live view. *Size: M. Depends:
  F-C.3, F-E.2.*

### F-L. Compliance & secure deployment
- **F-L.1 — Confidential-compute / air-gapped / on-prem deployment.** For
  sensitive or classified evaluation work. *Size: L. Depends: 8.3.*
- **F-L.2 — SIEM/EDR vendor integrations for real-defense arms.** Plug real
  commercial defenses into A/B arms. *Size: M. Depends: 6.1.*
- **F-L.3 — SOC2 / formal security posture.** For enterprise/SaaS. *Size: M.
  Depends: F-F.*

---

## Part B — Running improvements backlog

Concrete, individually-pickup-able items, including the deferrals v1 itself
created. Sizes: **S** ≤1 session, **M** 2–4 sessions, **L** 5+ sessions / an epic.
"Trigger" = the signal that it's time to do it.

| ID | Item | Size | Depends on | Trigger / why later |
|----|------|------|-----------|---------------------|
| B-01 | **2.6 snapshot/reset** (deferred from MVP) | M | 2.2, 2.5 | Needed before A/B (6.2) and efficient repeats (7.x); not needed for the single-run demo. |
| B-02 | **4.5 network telemetry** (deferred from MVP) | M | 2.3, 4.2 | Adds depth; model+host already proves "one timeline". Do before OpsEc/forensics. |
| B-03 | **Epic 5 — multi-agent (defender/users/policy)** | L | 3.x | The adversarial story; do right after MVP to unlock the differentiated demo. |
| B-04 | **Epic 6 — defense A/B + OpsEc** | L | 5.x, 2.6 | The "insert/remove a defense" pitch; the metric the field lacks. |
| B-05 | **Epic 7.1/7.2 — parallel campaigns at scale** | M–L | 3.4 | Needed for statistical power (high run variance) and buyer-grade reports. |
| B-06 | **8.2 self-observability (metrics/audit)** | M | 7.x, 4.2 | Needed to run Range as a service, not for a laptop demo. |
| B-07 | **8.3 full deploy (image/compose/Helm)** | M | 8.1, 8.2 | Needed for partner self-host; local compose subset comes earlier with 8.4. |
| B-08 | **ClickHouse `TraceStore` (F-C.1)** | M–L | 4.2 | DuckDB/Parquet query latency hurts at campaign scale, or analytics needs it. Migration, not rewrite (append-only + versioned schema). |
| B-09 | **Kafka/Redpanda ingestion (F-C.2)** | M | 4.2 | Concurrent ranges saturate direct writes, or live-view needs streaming. |
| B-10 | **Firecracker microVM backend (F-A.1)** | L | 2.1, 2.6 | First real fidelity tier; behind the existing `Backend` seam. |
| B-11 | **Windows/AD fidelity (F-B.1–B.3)** | L | F-A.1/A.2 | Reproduce the canonical enterprise (TLO/SpecterOps) class. Free via eval editions. |
| B-12 | **Self-hosted lab-host backend (F-B.4)** | M | F-A.1/A.2 | Build Windows+Linux VM ranges free on owned hardware (e.g. an unused PC) pre-cloud. |
| B-13 | **eBPF network policy (replaces iptables router rules)** | M | 2.3 | Richer/faster inter-host policy than the v1 router; do when network fidelity matters. |
| B-14 | **Richer pentest tooling image / fragment** | S–M | 2.5 | v1 attacker image is minimal; expand the toolset as scenarios demand. |
| B-15 | **Mythic (or equivalent) C2 integration** | M | 2.5, 3.2 | Match published range tooling (C2 framework as an agent tool) for realism. |
| B-16 | **Transcript clustering / failure-mode taxonomy (F-D.1)** | L | 4.6, B-08 | The "10k transcripts → conclusions" intelligence layer. |
| B-17 | **Anomaly baselining & detection models (F-D.2)** | L | 5.3, 6.3 | Directly attacks the "no baseline" gap; needs user-sim baselines first. |
| B-18 | **Web console (F-E)** | L | 4.6, 7.x, F-C.3 | CLI is enough for labs initially; UI for broader/SaaS reach. |
| B-19 | **SaaS multi-tenancy + auth + billing (F-F)** | L | 7.2, 8.2 | Only when going from "tool labs run" to "hosted product". |
| B-20 | **MITRE ATT&CK mapping (F-G.2)** | M | 1.3 | Standardized coverage reporting partners will ask for. |
| B-21 | **Range library expansion (F-G.1)** | ongoing | 1.3, fidelity | More fragments/ranges = more value per scenario authored. |
| B-22 | **RL environment export (F-I)** | L | 5.x, 4.x | Turns measurement into training-data generation; strategically adjacent to infra buyers. |
| B-23 | **ICS/OT digital twins (F-J)** | L | F-A | The "Cooling Tower" physical-consequence class. |
| B-24 | **Human-in-the-loop re-steering (F-K.2)** | M | F-C.3, F-E.2 | A key published threat model (human re-steers agent at bottlenecks). |
| B-25 | **Real SIEM/EDR vendor integrations (F-L.2)** | M | 6.1 | Real commercial defenses in A/B arms for enterprise credibility. |
| B-26 | **Distributed multi-node scheduling (F-H.1)** | L | 7.1, 7.2, cloud backend | Campaigns outgrow one control host. |
| B-27 | **OpenTelemetry export (F-C.4)** | S–M | 4.2 | Partners want Range data in their own observability stacks. |
| B-28 | **Confidential-compute / air-gapped deploy (F-L.1)** | L | 8.3 | Sensitive/classified evaluation engagements. |
| B-29 | **Managed-sandbox `CloudBackend` (Modal / E2B / Firecracker pool)** | M–L | 2.1, B-10 | Burst many parallel runs without managing VMs, behind the existing `Backend` seam. Modal/E2B already run gVisor sandboxes; natural fit once campaigns (7.x) outgrow the single OCI host. |
| B-30 | **gVisor + Docker service-discovery spike (embedded-DNS workaround)** | S | 2.3 | Docker's embedded DNS (127.0.0.11) on user-defined bridges does not work under `runsc`; validate name resolution early and pick a workaround (router-resolver / `--link` / hosts-file injection). Feeds 2.3/2.4. |
| B-31 | **OCIR golden-image registry** | S–M | 2.5, cloud backend | v1 caches golden images locally on the single host; a shared OCI Container Registry is needed once images are built once and run on many hosts/workers. |
| B-32 | **Remote Terraform state (OCI Object Storage backend) + guarded `apply` in CI** | S | 0.3 | v1 uses local TF state (single operator). Move to a remote backend with locking when >1 operator or CI-driven infra; enables a reviewed `apply` job. |
| B-33 | **Self-hosted CI runner on the OCI runsc host** | S–M | 0.3, 2.2 | GitHub-hosted CI runs unit + fake-backend only; a self-hosted runner on the runsc host lets the `@pytest.mark.docker`/`gvisor` suite run in CI rather than only nightly/on-host. |
| B-34 | **Managed secret store (OCI Vault) for model-provider keys** | S–M | 0.3, 3.1 | v1 supplies `RANGE_*` API keys via host environment (`SecretStr` in config). A managed Vault (with rotation + least-privilege retrieval) is needed once Range runs unattended / multi-operator / as a service. Keys never enter images, VCS, or TF state in either case. |
| B-35 | **OCI managed PostgreSQL for the trace index** | M | 4.2 | v1 runs Postgres as an on-host docker-compose container (data on the block volume). A managed DB (backups, HA, scaling) is wanted once the index outgrows one host or needs durability guarantees beyond the single VM. `TraceStore` callers unaffected (just a `postgres_url` change). |
| B-36 | **Object storage as the default blob store + retention/lifecycle policy** | S–M | 4.2, 4.5 | v1 defaults Parquet/PCAP to the block volume; the OCI Object Storage bucket is present in Terraform but gated off. Flip it on (and add a lifecycle/retention policy) once blob volume grows — PCAP capture (4.5) is the likely first trigger. |

**Maintenance rule:** whenever a v1 step makes a "good enough for now" choice
(e.g. DuckDB over ClickHouse, iptables over eBPF, minimal scaffold over expert
scaffolds), it must add a row here with the upgrade and its trigger — so the "no
tech debt" promise stays honest and the backlog stays the single source of truth
for "later."
