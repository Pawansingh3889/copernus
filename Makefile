.PHONY: help setup test gate lint fmt typecheck imports guards coverage-floors gate-proof \
        db-up db-down migrate serve clean

PY := uv run
GUARDS := scripts/check_module_size.py \
          scripts/check_no_secrets_in_contracts.py \
          scripts/check_no_python_in_markdown.py \
          scripts/check_no_windows_paths.py \
          scripts/check_doc_freshness.py

help:
	@echo "make setup           Install dependencies"
	@echo "make db-up           Start Postgres (podman-compose)"
	@echo "make migrate         Apply alembic migrations"
	@echo "make serve           Run the dev server"
	@echo "make test            Run the test suite"
	@echo "make gate            Every architecture check (what CI runs)"
	@echo "make gate-proof      Prove each gate rejects a planted violation"

setup:
	uv sync

db-up:
	podman-compose up -d
	@until podman exec copernus-db pg_isready -U copernus -q; do sleep 0.5; done
	@echo "postgres ready"

db-down:
	podman-compose down

migrate:
	$(PY) alembic upgrade head

serve:
	$(PY) uvicorn copernus.app:create_app --factory --reload --port 8010

test:
	$(PY) pytest

lint:
	$(PY) ruff check src tests scripts
	$(PY) ruff format --check src tests scripts

fmt:
	$(PY) ruff format src tests scripts

typecheck:
	$(PY) mypy

imports:
	$(PY) lint-imports

guards:
	@for guard in $(GUARDS); do \
		echo "--> $$guard"; \
		$(PY) python $$guard || exit 1; \
	done

# Coverage floors need a coverage report, so this target produces one first.
coverage-floors:
	$(PY) pytest --cov --cov-report=json --cov-report=term-missing
	$(PY) python scripts/check_coverage_floors.py

# gate-proof is what makes the rest of this file trustworthy: it plants a
# deliberate violation for each guard and asserts a non-zero exit. A gate that
# has never been observed to reject anything is decoration.
gate-proof:
	$(PY) pytest tests/test_gates.py -v

gate: lint imports guards coverage-floors gate-proof
	@echo ""
	@echo "All gates passed, and each was proven to fail on a planted violation."

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov coverage.json .coverage
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
