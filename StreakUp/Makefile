PYTHON ?= python3
NPM ?= npm

BACKEND_DIR := backend
FRONTEND_DIR := frontend

VENV_DIR := $(BACKEND_DIR)/.venv
PIP := $(VENV_DIR)/bin/pip
PYTHON_BIN := $(VENV_DIR)/bin/python

DB_PATH := data/app.db
SCHEMA_PATH := data/db/schema.sql
SEED_PATH := data/db/seed.sql
DEV_USER_SEED_PATH := data/db/dev_users_seed.sql
DB_URI := sqlite:////$(abspath $(DB_PATH))

CAP := npx cap
CAP_CONFIG := $(FRONTEND_DIR)/capacitor.config.json
ANDROID_DIR := android
APK_DEBUG_PATH := $(ANDROID_DIR)/app/build/outputs/apk/debug/app-debug.apk

GRADLE_USER_HOME ?= /tmp/streakup-gradle
OFFLINE_MODE ?= false
API_URL ?=

.PHONY: help venv install_requirements run_backend run_backend_prod run_frontend run_local dev \
	test test_all test_backend test_frontend test_frontend_unit test_e2e test_frontend_e2e test_perf test_frontend_perf \
	test_rf test_rnf test_requirements lint_frontend phase6_validate \
	build_frontend build_frontend_mobile sync_android open_android build_apk update-apk-auto \
	db-init db-init-demo db-bootstrap-catalog db-open db-clean db-reset db-dump db-backup db-psql db-diag

# ================================
# HELP
# ================================
help: ## Show available make commands
	@echo "Commands:"; grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/: ##/' | awk 'BEGIN {FS="##"}; {printf "  %-20s %s\n", $$1, $$2}'

# ================================
# ENV
# ================================
venv: ## Create the backend virtual environment when missing
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating virtual environment at $(VENV_DIR)"; \
		$(PYTHON) -m venv $(VENV_DIR); \
	else \
		echo "Virtual environment already exists"; \
	fi

install_requirements: venv ## Install backend and frontend dependencies
	@echo "Installing backend requirements"
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt
	@echo "Installing frontend dependencies"
	cd $(FRONTEND_DIR) && $(NPM) install

# ================================
# RUN
# ================================
run_backend: ## Start the backend development server
	@test -x "$(PYTHON_BIN)" || (echo "Run: make venv" && exit 1)
	@echo "Starting backend..."
	$(PYTHON_BIN) $(BACKEND_DIR)/run.py

run_backend_prod: ## Start the backend with Gunicorn
	@test -x "$(BACKEND_DIR)/.venv/bin/gunicorn" || (echo "Run: make install_requirements" && exit 1)
	@echo "Starting backend with Gunicorn..."
	cd $(BACKEND_DIR) && PORT=$${PORT:-5000} ./.venv/bin/gunicorn --bind 0.0.0.0:$${PORT:-5000} run:app

run_frontend: ## Start the frontend development server
	@echo "Starting frontend..."
	cd $(FRONTEND_DIR) && NEXT_PUBLIC_OFFLINE_MODE="false" $(NPM) run dev

run_local: ## Start the frontend in offline mode
	@echo "Frontend in OFFLINE mode"
	cd $(FRONTEND_DIR) && NEXT_PUBLIC_OFFLINE_MODE="true" $(NPM) run dev

dev: ## Run backend and frontend development servers
	@echo "Running full stack..."
	@trap 'kill 0' EXIT INT TERM; \
	$(MAKE) run_backend & \
	$(MAKE) run_frontend & \
	wait

# ================================
# VALIDATION
# ================================
test: ## Run backend, frontend unit, E2E, and performance tests
	$(MAKE) test_backend
	$(MAKE) test_frontend
	$(MAKE) test_e2e
	$(MAKE) test_perf

test_all: test ## Alias for test

test_backend: ## Run all maintained backend tests
	cd $(BACKEND_DIR) && ./.venv/bin/python -m pytest

test_frontend: ## Run frontend unit tests
	cd $(FRONTEND_DIR) && $(NPM) test
	cd $(FRONTEND_DIR) && $(NPM) run test:rf
	cd $(FRONTEND_DIR) && $(NPM) run test:rnf

test_frontend_unit: test_frontend ## Alias for frontend unit tests

test_e2e: ## Run frontend E2E tests
	cd $(FRONTEND_DIR) && $(NPM) run test:e2e

test_frontend_e2e: test_e2e ## Alias for frontend E2E tests

test_perf: ## Run frontend performance tests
	cd $(FRONTEND_DIR) && $(NPM) run test:perf

test_frontend_perf: test_perf ## Alias for frontend performance tests

test_rf: ## Run RF requirement tests for backend and frontend
	cd $(BACKEND_DIR) && ./.venv/bin/python -m pytest tests/requirements/rf
	cd $(FRONTEND_DIR) && $(NPM) run test:rf

test_rnf: ## Run RNF requirement tests for backend and frontend
	cd $(BACKEND_DIR) && ./.venv/bin/python -m pytest tests/requirements/rnf
	cd $(FRONTEND_DIR) && $(NPM) run test:rnf
	cd $(FRONTEND_DIR) && $(NPM) run test:rnf:e2e

test_requirements: test_rf test_rnf ## Run RF and RNF requirement tests

lint_frontend: ## Run frontend lint
	cd $(FRONTEND_DIR) && $(NPM) run lint

phase6_validate: test_backend lint_frontend test_frontend_unit test_frontend_perf build_frontend build_frontend_mobile build_apk ## Run Phase 6 validation checks
	@echo "Phase 6 validation complete"

# ================================
# FRONT BUILD
# ================================
build_frontend: ## Build the frontend web app
	@echo "Building frontend..."
	cd $(FRONTEND_DIR) && NEXT_PUBLIC_OFFLINE_MODE="$(OFFLINE_MODE)" NEXT_PUBLIC_API_URL="$(API_URL)" $(NPM) run build

build_frontend_mobile: ## Build the frontend for Capacitor
	@echo "Building frontend for Capacitor..."
	cd $(FRONTEND_DIR) && NEXT_PUBLIC_OFFLINE_MODE="$(OFFLINE_MODE)" NEXT_PUBLIC_API_URL="$(API_URL)" $(NPM) run build:mobile

# ================================
# ANDROID
# ================================
sync_android: ## Sync the frontend build into the Android project
	cd $(FRONTEND_DIR) && NEXT_PUBLIC_OFFLINE_MODE="$(OFFLINE_MODE)" $(NPM) run sync:android

open_android: ## Open the Android project through Capacitor
	cd $(FRONTEND_DIR) && $(CAP) open android

build_apk: ## Build the Android debug APK
	cd $(ANDROID_DIR) && GRADLE_USER_HOME="$(GRADLE_USER_HOME)" ./gradlew assembleDebug
	@echo "APK ready at $(APK_DEBUG_PATH)"

update-apk-auto: ## Sync Android assets and build the debug APK
	@$(MAKE) sync_android
	@$(MAKE) build_apk

# ================================
# DATABASE 🔥
# ================================

db-init: ## Crear DB local desde cero con schema + catálogo
	@echo "Initializing DB..."
	@mkdir -p data
	@test -x "$(PYTHON_BIN)" || (echo "Run: make venv" && exit 1)
	@test -f $(SCHEMA_PATH) || (echo "❌ schema.sql not found at $(SCHEMA_PATH)" && exit 1)
	@rm -f $(DB_PATH)
	sqlite3 $(DB_PATH) < $(SCHEMA_PATH)
	@$(MAKE) db-bootstrap-catalog
	@echo "✅ DB ready at $(DB_PATH)"

db-init-demo: ## Crear DB local con catálogo + usuarios demo
	@$(MAKE) db-init
	@test -f $(DEV_USER_SEED_PATH) || (echo "❌ dev_users_seed.sql not found at $(DEV_USER_SEED_PATH)" && exit 1)
	sqlite3 $(DB_PATH) < $(DEV_USER_SEED_PATH)
	@echo "✅ Demo users seeded at $(DB_PATH)"

db-bootstrap-catalog: ## Ejecutar bootstrap idempotente del catálogo
	@test -x "$(PYTHON_BIN)" || (echo "Run: make venv" && exit 1)
	cd $(BACKEND_DIR) && FLASK_ENV=development DATABASE_URL="$(DB_URI)" ./.venv/bin/flask --app run.py seed-catalog

db-reset: ## Reset DB (alias)
	$(MAKE) db-init

db-open: ## Open the local SQLite database
	@test -f $(DB_PATH) || (echo "Run: make db-init" && exit 1)
	sqlite3 $(DB_PATH)

db-psql: ## Open psql using DATABASE_URL from backend/.env.local
	@command -v psql >/dev/null 2>&1 || { echo "psql is not installed. Install the PostgreSQL client and try again."; exit 1; }
	@test -f $(BACKEND_DIR)/.env.local || (echo "Missing $(BACKEND_DIR)/.env.local" && exit 1)
	@set -a; \
	. $(BACKEND_DIR)/.env.local; \
	set +a; \
	test -n "$$DATABASE_URL" || { echo "DATABASE_URL is not set in $(BACKEND_DIR)/.env.local"; exit 1; }; \
	psql_url=$$(echo "$$DATABASE_URL" | sed 's|^postgresql+[^:]*://|postgresql://|; s|^postgres://|postgresql://|'); \
	echo "Opening psql session using DATABASE_URL from $(BACKEND_DIR)/.env.local..."; \
	exec psql "$$psql_url"

db-clean: ## Remove the local SQLite database
	@rm -f $(DB_PATH)
	@echo "🧹 DB removed"

db-dump: ## Dump the local SQLite database
	sqlite3 $(DB_PATH) ".dump"

db-backup: ## Back up the local SQLite database
	@mkdir -p data/backups
	@ts=$$(date +"%Y-%m-%d_%H%M%S"); \
	cp $(DB_PATH) data/backups/app_$$ts.sqlite && \
	echo "Backup saved"

open-db: ## Open Supabase/Postgres DB using DATABASE_URL from backend/.env.local
	@set -a; . backend/.env.local; set +a; \
	psql_url=$$(echo "$$DATABASE_URL" | sed 's|^postgresql+[^:]*://|postgresql://|; s|^postgres://|postgresql://|'); \
	psql "$$psql_url"

db-diag: ## Print sanitized DATABASE_URL breakdown (no password printed)
	@test -f $(BACKEND_DIR)/.env.local || { echo "Missing $(BACKEND_DIR)/.env.local"; exit 1; }
	@set -a; \
	. $(BACKEND_DIR)/.env.local; \
	set +a; \
	test -n "$$DATABASE_URL" || { echo "DATABASE_URL is not set in $(BACKEND_DIR)/.env.local"; exit 1; }; \
	url="$$DATABASE_URL"; \
	scheme=$$(echo "$$url" | sed 's|://.*||'); \
	rest=$$(echo "$$url" | sed 's|[^:]*://||'); \
	userinfo=$$(echo "$$rest" | sed 's|@.*||'); \
	user=$$(echo "$$userinfo" | sed 's|:.*||'); \
	hostpart=$$(echo "$$rest" | sed 's|[^@]*@||' | sed 's|/.*||'); \
	host=$$(echo "$$hostpart" | sed 's|:.*||'); \
	port=$$(echo "$$hostpart" | sed 's|[^:]*||; s|:||'); \
	db=$$(echo "$$rest" | sed 's|[^@]*@[^/]*/||' | sed 's|?.*||'); \
	psql_scheme=$$(echo "$$scheme" | sed 's|+[^+]*$$||; s|^postgres$$|postgresql|'); \
	echo ""; \
	echo "DATABASE_URL breakdown (password hidden):"; \
	echo "  raw scheme : $$scheme"; \
	echo "  psql scheme: $$psql_scheme  (driver suffix stripped for psql)"; \
	echo "  user       : $$user"; \
	echo "  host       : $$host"; \
	echo "  port       : $$port"; \
	echo "  database   : $$db"; \
	echo ""; \
	echo "$$user" | grep -qE '^postgres\.[a-zA-Z0-9]+$$' \
	  && echo "  [OK]  username matches Supabase pooler format  postgres.<project_ref>" \
	  || echo "  [WARN] username '$$user' does NOT match expected Supabase pooler format  postgres.<project_ref>"; \
	echo "$$port" | grep -q "^6543$$" \
	  && echo "  [OK]  port 6543 is correct for Supabase Transaction Pooler" \
	  || echo "  [INFO] port $$port (Supabase Transaction Pooler uses 6543, Session Pooler uses 5432)"; \
	echo ""
