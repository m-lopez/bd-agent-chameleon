# bd-agent-chameleon

Always-on agent workers that poll for and execute tasks from a [beads](https://github.com/steveyegge/beads) instance. Each worker adopts a configurable role -- a persona with its own system prompt and agent type -- then claims matching tasks and launches Claude sessions to complete them.

Orchestration logic lives in a layer above this. Beads defines the task graph; `bd-agent-chameleon` is the runtime that consumes it.

## Features

- **Fresh context per task.** Every task runs in its own Claude session, avoiding stale state.
- **Role-based routing.** Tasks are labeled and matched to roles defined in a TOML config, so a single fleet can host specialized workers side by side.

## Motivating use case

Consider orchestrating a multi-stage agent flow for a microservice project with opinionated conventions around implementation and testing:

1. A developer writes a short description of a new service.
2. Architect and PM agents elaborate the description into a tailored RFC.
3. The developer reviews and refines the RFC.
4. Epic agents break the RFC into beads epics (observability, e2e testing, implementation, etc.), each with concrete tasks.
5. Worker chameleons pick up the tasks. Each task carries a label that routes it to the right role and Claude subagent.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- [Claude CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude`) on `PATH`
- [beads](https://github.com/steveyegge/beads) CLI (`bd`) on `PATH`, with a local database directory

## Building and installing

```bash
# Clone the repository
git clone https://github.com/<org>/bd-agent-chameleon.git
cd bd-agent-chameleon

# Install dependencies
uv sync

# Install the CLI globally (editable)
make install

# Run the full check suite (lint + typecheck + tests)
make check
```

See `make help` for all available targets.

## Usage

### Role configuration

Define roles in a TOML file. Each role specifies a system prompt, whether the session is interactive, and an optional agent type:

```toml
# roles.toml
[implementer]
prompt = "Implement the task described below."
interactive = false
agent = "senior-microservices-backend-engineer"

[reviewer]
prompt = "You are a code reviewer. Review the diff and leave comments."
interactive = false

[rfc-reviewer]
prompt = ""
interactive = false
```

### Running a worker

```bash
bd-agent-chameleon run \
  --role implementer \
  --config roles.toml \
  --db /path/to/beads/db \
  --poll-interval 5.0
```

The worker will poll the beads database for tasks labeled `role-implementer`, claim each one, launch a Claude session with the configured prompt, and mark the task as complete.

## Project layout

```
src/bd_agent_chameleon/
  main.py               # CLI entry point (typer)
  chameleon.py          # Core poll-execute loop
  config_manager.py     # TOML role loader
  beads_task_manager.py # Beads database adapter
  claude_launcher.py    # Claude session launcher
  models.py             # Task and Role data types
  protocols.py          # Abstract interfaces (TaskManager, SessionLauncher)
```

## License

Apache 2.0. See [LICENSE](LICENSE) for details.
