.PHONY: test validate golden fixtures reproduce reproduce-full mutation coverage install-dev smoke offline-bundle docker acceptance plan

# The whole suite (same as: python -m pytest). Skipped tests print their reason.
test:
	python -m pytest

# Exact environment for reproducing results (pinned runtime + coverage/random-order tools)
install-dev:
	python -m pip install -r requirements-dev.txt

# One command to every reported number: regenerate synthetic data, run tests + coverage + random order,
# chat benchmark, red-team set; diff against the committed results; writes results/ (see REPRODUCE.md)
reproduce:
	python scripts/reproduce.py

# The same plus the mutation check (slow: one test-suite run per planted bug)
reproduce-full:
	python scripts/reproduce.py --mutation

mutation:
	python scripts/mutation_check.py

coverage:
	python -m pytest --cov --cov-report=term

validate:
	python -m core.validate

golden:
	python -m pytest tests/golden

# Regenerate golden JSON from fixtures/build_fixtures.py (only when you mean to change a fixture)
fixtures:
	python fixtures/build_fixtures.py

# Fresh-install / deployment check: parse, engine, voice clip, registry, report, app health, no network egress
smoke:
	python scripts/smoke.py

# Offline install bundle (wheels + repo) for a computer with no internet; see DEPLOY.md
offline-bundle:
	python scripts/make_offline_bundle.py

docker:
	docker compose build && docker compose up -d && docker compose ps

# Final acceptance list (Q5): every item with its command and pass/fail
acceptance:
	python scripts/acceptance.py

plan:
	python scripts/plan_vs_delivered.py
