.PHONY: dev down test lint typecheck build migrate
dev:
	docker compose up --build
down:
	docker compose down
test:
	docker compose run --rm api pytest -q /app/tests
lint:
	docker compose run --rm api ruff check .
	docker compose run --rm web npm run lint
typecheck:
	docker compose run --rm web npm run typecheck
build:
	docker compose build web
migrate:
	docker compose run --rm api alembic upgrade head
