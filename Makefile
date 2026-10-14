# NutriGent tasks. Build automation is pip (pyproject.toml); make only wraps the commands.
PYTHON ?= python3
VENV   ?= .venv
PY      = $(VENV)/bin/python
UNIT    = $(sort $(wildcard tests/test_*.py))

.PHONY: help install test e2e run report clean

help:
	@echo "make install   create $(VENV) and pip-install the project"
	@echo "make test      run every unit suite (stops at the first failure)"
	@echo "make e2e       80 scripted actions against a simulated Telegram API"
	@echo "make run       start the bot (needs .env with TELEGRAM_TOKEN)"
	@echo "make report    build report/main.pdf with tectonic"
	@echo "make clean     remove caches, test databases and LaTeX output"

$(PY):
	$(PYTHON) -m venv $(VENV)

install: $(PY)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e .

test:
	@set -e; for t in $(UNIT); do echo "== $$t"; MPLBACKEND=Agg $(PYTHON) $$t; done

e2e:
	MPLBACKEND=Agg HERMES_BIN=/nonexistent $(PYTHON) tests/e2e_fake_telegram.py build/e2e

run:
	set -a; . ./.env; set +a; $(PYTHON) app/bot.py

report:
	cd report && tectonic main.tex

clean:
	rm -rf build .pytest_cache *.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	cd report && rm -f *.aux *.log *.out *.toc *.bbl *.blg *.lof *.lot *.synctex.gz main.pdf
