# 4. Infrastructure as code: Terraform on a single OCI x86 host

Date: 2026-05-29

## Status

Accepted

## Context

Range's v1 execution substrate is a single paid **OCI x86 VM** running Docker +
gVisor (`runsc`), with the control plane co-located there (design decision **D9**,
`docs/RANGE_DESIGN_V1.md` §5). "Test as we go" needs that substrate to be
reproducible and version-controlled from the first infra need — the
`@pytest.mark.docker` integration tests (2.2+) run against it. This step (0.3)
stands the host up; every later infra need extends the same module surgically,
one resource at a time.

## Decision

All OCI resources are declared in **Terraform** under `deploy/terraform/`. A root
`main.tf` composes two child modules — `modules/network` (VCN, public subnet, NSG)
and `modules/compute` (the `E4.Flex` instance, cloud-init, block volume). This is
the operator's preferred layout and a deliberate departure from the shared
standards' "flat root module / YAGNI" guidance: the host is the seed of the infra,
so its concerns are split now and later steps add resources into the module they
belong to. 0.3 provisions only the host: VCN, public subnet, an NSG (preferred
over security lists), an `E4.Flex` instance bootstrapped by cloud-init (Docker CE
+ `runsc` + Python 3.12/uv), and a block volume mounted at `/data` for Docker
layers and trace state. No console-created resources; `apply`/`destroy` are
operator actions, never run in CI. CI runs
`fmt -check` + `init -backend=false` + `validate` only. Secrets never enter state
or VCS: real values live in a git-ignored `terraform.tfvars`, with
`terraform.tfvars.example` committed.

Two specifics decided during implementation:

- **Provider source is `oracle/oci`, not `hashicorp/oci`.** The shared-standards
  prose names `hashicorp/oci`, but no such provider exists — the official OCI
  provider is published under the `oracle` namespace on the Terraform Registry,
  which is what the step's own `versions.tf` snippet uses. The package wins; the
  standards prose is the typo.
- **Host egress allows TCP 80 in addition to 443 + DNS.** The step specified
  egress 443 + 53 only, but OCI's Ubuntu images point `apt` at **http** mirrors
  (port 80), so cloud-init's `apt-get` would fail and the host would never finish
  bootstrapping. Port 80 is opened for the base Ubuntu archive only; range
  *container* egress is denied separately, in-Docker, by step 2.3.

## Consequences

- Infra changes are reviewed via `terraform plan`, applied by the operator, and
  proven by a post-apply smoke check (`make host-smoke`) before dependent code
  merges — the same surgical, per-step discipline as the application code.
- The host is stoppable to control cost; the block volume preserves state across
  stop/start and instance recreation.
- Deferred (backlog): remote TF state on OCI Object Storage (**B-32**), a
  self-hosted CI runner on the host (**B-33**), and a managed-sandbox / cloud
  backend swap (**B-29**).
- ADR number is 0004 (not the 0003 the step text names) because 0003 was already
  taken by the step-0.2 logging ADR.
