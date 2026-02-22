.PHONY: build up down test lint format integration-test

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

test:
	pytest tests/test_auth.py tests/test_mcp.py

lint:
	ruff check src/safeclaw tests
	mypy src/safeclaw

format:
	ruff format src/safeclaw tests

integration-test: up
	RUN_INTEGRATION_TESTS=1 pytest tests/integration/test_docker.py
	docker-compose down
