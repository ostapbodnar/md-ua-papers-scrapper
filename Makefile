up: ## Bring up the services in the development environment
	docker compose --profile dev up -d

up-prod: ## Bring up the services in the production environment
	docker compose --profile prod up -d

down: ## Bring down the services
	docker compose --profile dev down

build: ## Build the services in the development environment
	docker compose --profile prod build


logs: ## Tail logs for all services in the environment
	docker compose --profile dev  logs -f

logs-prod: ## Tail logs for all services in the production environment
	docker-compose --profile prod logs -f

help: ## Show this help
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##"; printf "\033[1m%-15s\033[0m %s\n", "Target", "Description"} /^[a-zA-Z_-]+:.*##/ { printf "\033[1m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
