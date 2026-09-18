.PHONY: help start stop clean ps logs dbt-run

help:
	@echo "Comandos: start stop clean ps logs dbt-run"

start:
	docker-compose up -d
	@echo "Airflow: http://localhost:8080 (admin/admin)"
	@echo "Dashboard: http://localhost:8501"
	@echo "API: http://localhost:8000/docs"

stop:
	docker-compose down

clean:
	docker-compose down -v --rmi all

ps:
	docker-compose ps

logs:
	docker-compose logs -f

dbt-run:
	cd transform/dbt_models && dbt run --profiles-dir . --target dev
