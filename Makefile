PG_CONTAINER ?= aggregation_postgres
VENV_PYTEST   := .venv/Scripts/pytest.exe

.PHONY: test test-aggregation test-markets test-orderbooks test-user pgvector

## Run tests for aggregation_service
test-aggregation:
	cd aggregation_service && ../$(VENV_PYTEST) tests/ -q --tb=short

## Run tests for update_markets_service
test-markets:
	cd update_markets_service && ../$(VENV_PYTEST) tests/ -q --tb=short

## Run tests for update_orderbooks_service
test-orderbooks:
	cd update_orderbooks_service && ../$(VENV_PYTEST) tests/ -q --tb=short

## Run tests for user_service
test-user:
	cd user_service && ../$(VENV_PYTEST) tests/ -q --tb=short

## Run tests for all services
test: test-aggregation test-markets test-orderbooks test-user

.PHONY: pgvector
pgvector:
	docker exec -it $(PG_CONTAINER) sh -lc '\
		echo "https://dl-cdn.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories && \
		apk update && \
		apk add clang19 llvm19 llvm19-dev && \
		apk add --no-cache build-base clang llvm llvm-dev postgresql-dev git && \
		if [ ! -d pgvector ]; then git clone https://github.com/pgvector/pgvector.git; fi && \
		cd pgvector && \
		make && \
		make install \
	'