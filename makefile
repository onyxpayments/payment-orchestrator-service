venv:
	python3 -m venv .venv

install: venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

format:
	.venv/bin/black .

lint:
	.venv/bin/black --check app adapters migrations tests
	.venv/bin/flake8 app adapters migrations tests

test:
	.venv/bin/pytest -vv

migrate:
	.venv/bin/alembic upgrade head

test-integration:
	.venv/bin/pytest -vv tests/integration

docker-build:
	docker build -t payment-orchestrator-service .
