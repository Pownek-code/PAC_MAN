PYTHON  ?= python3
VENV    := .venv
PY      := $(VENV)/bin/python
CONFIG  ?= config.json
WHEEL   := $(wildcard mazegenerator-*.whl)

.PHONY: install run debug clean lint lint-strict test package

install:
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements-dev.txt
	$(PY) -m pip install --force-reinstall --no-deps $(WHEEL)

run:
	$(PY) pac-man.py $(CONFIG)

debug:
	PACMAN_DEBUG=1 $(PY) -m pdb pac-man.py $(CONFIG)

clean:
	find . -path ./$(VENV) -prune -o -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache build dist

lint:
	$(PY) -m flake8 .
	$(PY) -m mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	$(PY) -m flake8 .
	$(PY) -m mypy . --strict

test:
	$(PY) -m pytest -q

package:
	@echo "Building with PyInstaller (output in dist/)"
	$(PY) -m PyInstaller --noconfirm --clean pac-man.spec
