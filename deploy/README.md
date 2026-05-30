# Range — deploy runbook

Infrastructure for Range's v1 host: a single OCI x86 VM running Docker + gVisor
(`runsc`), stood up by Terraform in [`terraform/`](terraform/). See
[ADR 0004](../docs/adr/0004-iac-terraform-oci.md) for the why; this file is the
operator how-to.

> All OCI resources live in Terraform. Never hand-create anything in the console —
> if it isn't in `deploy/terraform/`, it doesn't exist.

## Prerequisites

- Terraform ≥ 1.6 and an OCI account with a compartment you can deploy into.
- `~/.oci/config` configured with an API key (the provider auths from it).
- Your SSH public key and the OCIDs for your tenancy + compartment.

## First-time setup

```bash
cd deploy/terraform
cp terraform.tfvars.example terraform.tfvars   # git-ignored — fill in real values
# Edit terraform.tfvars: region, compartment_ocid, tenancy_ocid, ssh_public_key,
# and lock allowed_ssh_cidr to your IP (e.g. 203.0.113.4/32).
```

## Provision

From the repo root:

```bash
make tf-init       # one-time: download the oracle/oci provider
make tf-plan       # review the change
make tf-apply      # operator action — creates the host (never run in CI)
```

`tf-apply` prints `instance_public_ip` and `ssh_command`. First boot runs
cloud-init (Docker CE, runsc, Python 3.12/uv, /data volume); give it a couple of
minutes before the smoke check.

## Smoke check

```bash
make host-smoke
```

Passes when it shows the `runsc` runtime present, runs `hello-world` under
`--runtime=runsc`, and prints `uv --version`. To watch bootstrap or debug:

```bash
ssh ubuntu@$(cd deploy/terraform && terraform output -raw instance_public_ip)
tail -f /var/log/cloud-init-output.log     # on the host
```

## Stop / start (cost control)

The host is **stoppable** — stop it when idle and you pay only for boot + block
volume storage; the `/data` volume preserves Docker layers and trace state across
stops. Use the OCI console or CLI:

```bash
INSTANCE_ID=$(cd deploy/terraform && terraform output -raw instance_id)
oci compute instance action --action STOP  --instance-id "$INSTANCE_ID"
oci compute instance action --action START --instance-id "$INSTANCE_ID"
```

A restarted instance keeps its `/data` volume but may get a new public IP —
re-read `terraform output -raw instance_public_ip`.

## Teardown

```bash
make tf-plan       # should show "no changes" (no drift) before destroying
make tf-destroy    # removes the instance, volume, network — everything
```

Verify in the OCI console that no resources remain (no orphaned block volumes).

## What CI checks

CI's `infra` job runs `terraform fmt -check`, `init -backend=false`, and
`validate` only — it has no OCI creds and never `apply`s or `plan`s against real
OCI. Applies and the smoke check are operator actions, run here.
