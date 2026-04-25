.PHONY: install sync lint fmt type-check test test-cov api-dev ui-dev pre-commit-install clean

install:
	uv sync --all-packages

sync:
	uv sync --all-packages --upgrade

lint:
	uv run ruff check .

fmt:
	uv run ruff format .
	uv run ruff check --fix .

type-check:
	uv run mypy backend/src/prediction_trading/

test:
	uv run pytest backend/tests/ -v

test-cov:
	uv run pytest backend/tests/ -v --cov=prediction_trading --cov-report=html

api-dev:
	uv run uvicorn prediction_trading.api.main:app --reload --port 8000

ui-dev:
	uv run streamlit run frontend/app.py

pre-commit-install:
	uv run pre-commit install

pre-commit-run:
	uv run pre-commit run --all-files

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage
