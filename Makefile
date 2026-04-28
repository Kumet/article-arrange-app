SHELL := /bin/zsh

PYTHON ?= python3.11
VENV ?= .venv
PORT ?= 8000
MOCK_PORT ?= 8001
MOCK_URL ?= https://example.com/mock/original
MOCK_KEYWORD ?= SEO 記事 リライト
MOCK_PROMPT ?= 専門家向けに簡潔に

VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
PYTEST := $(VENV)/bin/pytest

.PHONY: help venv install setup env run run-mock test test-verbose compile check clean-db clean-pyc mock-request

help:
	@echo "Available commands:"
	@echo "  make setup        - create .venv, install dependencies, and create .env if missing"
	@echo "  make install      - install dependencies into .venv"
	@echo "  make env          - create .env from .env.example if missing"
	@echo "  make run          - run the app with current .env"
	@echo "  make run-mock     - run the app with OPENAI_MODEL=mock"
	@echo "  make test         - run pytest"
	@echo "  make compile      - run python -m compileall app"
	@echo "  make check        - run compile + pytest"
	@echo "  make mock-request - submit a mock article generation job to the local server"
	@echo "  make clean-db     - remove local SQLite database"
	@echo "  make clean-pyc    - remove Python cache files"

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

venv: $(VENV_PYTHON)

install: venv
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt

env:
	@if [ ! -f .env ]; then cp .env.example .env; echo ".env created from .env.example"; else echo ".env already exists"; fi

setup: install env

run: venv
	$(UVICORN) app.main:app --reload --host 127.0.0.1 --port $(PORT)

run-mock: venv
	OPENAI_MODEL=mock $(UVICORN) app.main:app --reload --host 127.0.0.1 --port $(MOCK_PORT)

test: venv
	$(PYTEST)

test-verbose: venv
	$(PYTEST) -vv

compile: venv
	$(VENV_PYTHON) -m compileall app

check: compile test

mock-request:
	curl -s -X POST http://127.0.0.1:$(MOCK_PORT)/jobs \
		-d 'original_url=$(MOCK_URL)' \
		--data-urlencode 'target_keyword=$(MOCK_KEYWORD)' \
		--data-urlencode 'user_prompt=$(MOCK_PROMPT)'

clean-db:
	rm -f app.db

clean-pyc:
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
