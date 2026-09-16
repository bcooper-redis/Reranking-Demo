.PHONY: up down seed test backend-test backend-integration-test frontend-test eval lint fmt

up:
	docker compose up --build

down:
	docker compose down

seed:
	docker compose run --rm seed python -m app.seed --reset --count 360

test: backend-test frontend-test

backend-test:
	cd backend && python3 -m pytest

backend-integration-test:
	cd backend && RUN_REDIS_INTEGRATION=1 REDIS_URL=$${REDIS_URL:-redis://localhost:6380} python3 -m pytest -m integration

frontend-test:
	cd frontend && npm test -- --run

eval:
	curl -s -X POST http://localhost:8000/api/v1/evaluations/run | python3 -m json.tool

lint:
	cd backend && python3 -m ruff check app tests
	cd frontend && npm run lint

fmt:
	cd backend && python3 -m ruff format app tests
	cd frontend && npm run format
