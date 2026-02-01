.PHONY: build test install uninstall lint format typecheck check help

build:
	uv build

test:
	uv run pytest

install:
	uv tool install -e .

uninstall:
	uv tool uninstall bd-agent-chameleon

lint:
	uv run ruff check src

format:
	uv run ruff format src

typecheck:
	uv run mypy src

check: lint typecheck test

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  build      Build wheel and sdist"
	@echo "  test       Run tests with pytest"
	@echo "  install    Install bd-agent-chameleon globally (editable)"
	@echo "  uninstall  Uninstall bd-agent-chameleon global tool"
	@echo "  lint       Run ruff linter"
	@echo "  format     Format code with ruff"
	@echo "  typecheck  Run mypy type checking"
	@echo "  check      Run lint + typecheck + test"
	@echo "  help       Show this help message"
