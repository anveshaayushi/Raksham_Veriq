.PHONY: validate test golden fixtures

validate:
	python3 -m core.validate

golden:
	python3 -m pytest tests/golden

test:
	python3 -m pytest

# Regenerate golden JSON from fixtures/build_fixtures.py (only when you mean to change a fixture)
fixtures:
	python3 fixtures/build_fixtures.py
