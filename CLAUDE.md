# CLAUDE.md

Read `pyproject.toml` to understand the project, its dependencies, and tooling.

## Planning

- `.planning/` contains planning files.
- EDDs (Engineering Design Documents) go in `.planning/edd/`, prefixed with a 4-digit integer (e.g. `0001-`). Numbers increase.
- Workflows go in `.planning/workflows/`, prefixed with a 4-digit integer. Numbers increase.

## Documentation

- Documentation is kept in `doc/`.

## Testing

- Run tests with `make test` (pytest).

## Coding standards

- Functions SHOULD under 10 lines unless it violates Python idiom.
- Functions SHOULD have a single responsibility. No big messy functions.
- All classes and functions MUST have docstring descriptions, even small ones.
- We MUST use strong typing when defining constants, function parameters, and variables.
  - Example: Old time interfaces may use a float for duration in seconds. Instead, specify the duration using datetime.timedelta and convert at the location where the seconds type is needed.
