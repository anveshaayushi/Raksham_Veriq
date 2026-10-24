.PHONY: validate test golden fixtures

# The whole suite (same as: python -m pytest). Skipped tests print their reason.
test:
	python -m pytest

validate:
	python -m core.validate

golden:
	python -m pytest tests/golden

# Regenerate golden JSON from fixtures/build_fixtures.py (only when you mean to change a fixture)
fixtures:
	python fixtures/build_fixtures.py
