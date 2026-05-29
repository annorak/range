.PHONY: install lint fmt types imports test check

install: ; uv sync
lint:    ; uv run ruff check . && uv run ruff format --check .
fmt:     ; uv run ruff format .
types:   ; uv run mypy
imports: ; uv run lint-imports
test:    ; uv run pytest
check: lint types imports test
