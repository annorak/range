.PHONY: install lint fmt types imports test check \
        tf-init tf-fmt tf-validate tf-plan tf-apply tf-destroy host-smoke

install: ; uv sync
lint:    ; uv run ruff check . && uv run ruff format --check .
fmt:     ; uv run ruff format .
types:   ; uv run mypy
imports: ; uv run lint-imports
test:    ; uv run pytest
check: lint types imports test

# --- Infra (Terraform → OCI). apply/destroy are operator actions, never CI.
tf-init:     ; cd deploy/terraform && terraform init
tf-fmt:      ; cd deploy/terraform && terraform fmt -recursive
tf-validate: ; cd deploy/terraform && terraform fmt -check -recursive && terraform validate
tf-plan:     ; cd deploy/terraform && terraform plan
tf-apply:    ; cd deploy/terraform && terraform apply
tf-destroy:  ; cd deploy/terraform && terraform destroy

# Post-apply smoke: runsc runtime present, hello-world runs under it, uv works.
host-smoke: ; @ssh ubuntu@$$(cd deploy/terraform && terraform output -raw instance_public_ip) \
  'docker info --format "{{.Runtimes}}" && docker run --runtime=runsc --rm hello-world && uv --version'
