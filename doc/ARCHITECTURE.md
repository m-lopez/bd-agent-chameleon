# Architecture

## Domain Model

bd-agent-chameleon is a runtime for agent orchestration. It polls a task management
system for work, resolves the appropriate role from each ticket's labels, and
launches Claude sessions to execute them. It is not an application framework —
output contracts, DAG design, and workflow logic are concerns of the flow authors
building on top of this runtime.

### Concepts

#### Role

Pure configuration that defines how a Claude session behaves.

| Field       | Type   | Description                                        |
|-------------|--------|----------------------------------------------------|
| name        | `str`  | Unique identifier for the role.                    |
| prompt      | `str`  | Initial system prompt passed to Claude.            |
| interactive | `bool` | If true, Claude runs interactively (no `--print`). |

Roles are resolved per-ticket from `role-*` labels (see below).

#### bd-agent-chameleon Instance

A running process that dynamically resolves roles from ticket labels.

- **Dynamic role resolution.** A single chameleon instance services tickets for
  any role. The role is determined per-ticket from a `role-X` label.
- **Polling label** is fixed: `chameleon-task`. All tickets intended for the
  chameleon carry this label.
- **Role source** is the `role-X` label on the ticket, where X is the role name.
  The role name is used as the `--agent` value and to look up configuration.
- **Lifecycle states:** `polling` -> `executing` -> `polling` -> `shutdown`.

During `polling`, the instance queries the task management system for open
tasks labeled `chameleon-task`. When a task is found, it transitions to
`executing`: it resolves the role from the ticket's labels, then launches
Claude with the role configuration and a workflow prompt that instructs Claude
to manage the ticket lifecycle (read, claim, work, close). It then returns to
`polling`.

#### Task Lifecycle Delegation

The chameleon no longer claims or completes tasks itself. Instead, the prompt
instructs Claude to manage the ticket lifecycle:

```
Use this workflow to execute the task in the ticket:
  - Read the ticket using: `bd show <TICKET_ID>`
  - Claim the ticket using: `bd update <TICKET_ID> --claim`
  - Do the work described in the ticket
  - Then close the ticket using: `bd close <TICKET_ID>`
```

This is safe because the chameleon processes one task at a time (synchronous
`subprocess.run` blocks until Claude exits).

#### Task Management System

An external system that the runtime integrates with. Currently
[beads](https://github.com/steveyegge/beads).

The runtime requires only one operation from the task management system:

1. **poll** — list tasks matching a label with status `open`.

Task claiming and completion are delegated to the Claude session via the
workflow prompt.

#### Task

A unit of work as seen by the runtime.

| Field       | Type                              | Description                                           |
|-------------|-----------------------------------|-------------------------------------------------------|
| id          | `str`                             | Unique identifier from the task system.               |
| title       | `str`                             | Short description of the work.                        |
| description | `str`                             | Detailed description of the work.                     |
| labels      | `list[str]`                       | Labels attached to the ticket.                        |
| status      | `open \| in_progress \| closed`   | Current lifecycle state.                              |

The runtime uses labels to determine the polling filter (`chameleon-task`) and
to resolve the role (`role-X`).

#### Document Store

A shared filesystem where Claude sessions read from and write to.

The runtime imposes no structure on the document store. Flow authors
define their own conventions for organizing output artifacts.

#### Human Operator

A person who interacts with the system in two capacities:

- **Task creator** — authors tasks in the task management system with
  `chameleon-task` and `role-X` labels. This happens outside the runtime.
- **Session interactor** — provides input to Claude sessions running in
  interactive mode (i.e., when a role has `interactive: true`).

Recovery of stuck tasks (e.g., an `in_progress` task whose bd-agent-chameleon
process crashed) is currently a manual operation performed by the human
operator.

### Out of Scope

The following are explicitly not concerns of this runtime:

- **Task selection strategy** — the runtime takes the first available task.
  Configurable selection policies may be added later.
- **Output contracts** — flow authors define what Claude sessions produce.
- **Task spawning** — Claude sessions do not create tasks as part of this
  runtime.
- **Alerting and notifications** — hooks for alerts may be added later.
- **Dead letter / orphan recovery** — automated recovery of stuck tasks is
  a future enhancement.

### Open Questions

1. **Role config format** — where does role configuration live? A TOML/YAML
   file? CLI flags? This determines how role names from ticket labels resolve
   to prompt, and interactive settings.
2. **Beads integration surface** — should the runtime shell out to the `bd`
   CLI with `--json` output, or use a Python abstraction layer? An
   abstraction would make the task management system swappable.

## Component Architecture

### Overview

```
┌──────────────────────────────────────────────────────────┐
│                      CLI (typer)                         │
│           bd-agent-chameleon --config ...                  │
│                                                          │
│  Wires dependencies:                                     │
│    config_mgr = ConfigManager(...)                       │
│    task_mgr   = BeadsTaskManager(...)                    │
│    launcher   = ClaudeLauncher(...)                      │
│    chameleon  = Chameleon(config_mgr, task_mgr,          │
│                           launcher)                      │
│    chameleon.run()                                       │
└───────────────────────────┬──────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────┐
│                      Chameleon                           │
│                                                          │
│  __init__(config_mgr, task_mgr, launcher)                │
│  run() → main loop                                       │
│                                                          │
│  States: polling → executing → polling → shutdown        │
│                                                          │
│  _poll() → polls with "chameleon-task" label             │
│  _resolve_role(task) → extracts role-X from labels       │
│  _execute() → resolves role, launches session            │
└─────────┬──────────────┬───────────────────┬─────────────┘
          │              │                   │
          ▼              ▼                   ▼
┌────────────┐ ┌──────────────┐ ┌────────────────────────┐
│TaskManager │ │ConfigManager │ │SessionLauncher         │
│«protocol»  │ │              │ │«protocol»              │
│            │ │- load_role() │ │                        │
│- poll()    │ │→ Role | None │ │- launch(Role|None,Task)│
└─────┬──────┘ └──────────────┘ └──────────┬─────────────┘
      │ implements                         │ implements
      ▼                                    ▼
┌──────────────┐                  ┌─────────────────┐
│BeadsTaskMgr  │                  │ClaudeLauncher   │
└──────────────┘                  └─────────────────┘
```

### Components

#### Chameleon

The core orchestrator. Receives all dependencies via constructor injection.

- Owns the state machine: `polling` → `executing` → `polling` → `shutdown`.
- During `polling`, calls `TaskManager.poll("chameleon-task")`.
- During `executing`, resolves the role from the task's labels via
  `ConfigManager.load_role()`, then delegates to `SessionLauncher.launch()`.
- Handles graceful shutdown (signals, quit key).

Chameleon contains no knowledge of how tasks are fetched, how config is
loaded, or how Claude is invoked. It only coordinates.

#### TaskManager (protocol)

Adapter interface to the external task management system.

```
TaskManager
  poll(label: str) → list[Task]
```

`TaskManager` is a `typing.Protocol`. Concrete implementations speak
the external system's language. The first implementation is
`BeadsTaskManager`, which shells out to the `bd` CLI.

#### ConfigManager

Loads and provides Role configurations. Resolves a role name to a full
`Role` dataclass, or returns `None` if the role is not found.

```
ConfigManager
  load_role(name: str) → Role | None
```

The config source format (TOML, YAML, CLI flags) is an implementation
detail of ConfigManager. The rest of the system only sees `Role`.

#### SessionLauncher (protocol)

Builds and runs a Claude session.

```
SessionLauncher
  launch(role: Role | None, task: Task) → None
```

`SessionLauncher` is a `typing.Protocol`. The concrete implementation
is `ClaudeLauncher`, which:

- Composes the final prompt from optional `role.prompt` + workflow template.
- Builds the Claude CLI invocation (`--print`, `--agent` flags).
- Manages terminal state (tty save/restore).
- Runs Claude as a subprocess.

SessionLauncher owns the **prompt composition** — it decides how
Role and Task content combine into the Claude input, including the
workflow instructions for ticket lifecycle management.

### Data Types

| Type   | Kind      | Fields                                     |
|--------|-----------|--------------------------------------------|
| `Role` | dataclass | `name`, `prompt`, `interactive`            |
| `Task` | dataclass | `id`, `title`, `description`, `status`, `labels` |

### Data Flow (Single Task Cycle)

```
Chameleon.run()
  │
  ├─ polling
  │   └─→ TaskManager.poll("chameleon-task") → [Task, ...]
  │
  ├─ executing
  │   ├─→ extract_role_name(task.labels) → "reviewer" (or None)
  │   ├─→ ConfigManager.load_role("reviewer") → Role (or None)
  │   └─→ SessionLauncher.launch(role, task)
  │         ├─ compose prompt: [role.prompt] + workflow template
  │         ├─ build: claude <prompt> [--print] [--agent reviewer]
  │         ├─ save/restore tty state
  │         └─ subprocess.run(...)
  │
  └─ back to polling
```

### Design Decisions

1. **Constructor injection.** Chameleon receives `TaskManager`,
   `ConfigManager`, and `SessionLauncher` via `__init__`. The CLI
   layer wires the concrete implementations. This makes testing
   straightforward — inject mocks/fakes without patching.

2. **Protocols for TaskManager and SessionLauncher.** Both are
   `typing.Protocol` classes. TaskManager is a protocol because the
   architecture explicitly targets swappable task systems.
   SessionLauncher is a protocol to support testing (mock launcher)
   and future alternatives (e.g., dry-run mode).

3. **SessionLauncher owns prompt composition.** When a task is
   found, Chameleon passes both the optional `Role` and `Task` to
   `SessionLauncher.launch()`. The launcher decides how to combine
   `role.prompt` with the workflow template into the final Claude
   input. This keeps Chameleon free of prompt formatting concerns.

4. **ConfigManager is a concrete class.** Unlike TaskManager and
   SessionLauncher, there is no immediate need for multiple config
   backends. A protocol can be extracted later if needed.

5. **Dynamic role resolution.** A single chameleon instance services
   all roles. The role is resolved per-ticket from `role-*` labels,
   eliminating the need for one process per role.

6. **Delegated task lifecycle.** The chameleon no longer claims or
   completes tasks. Instead, the workflow prompt instructs Claude to
   manage the ticket lifecycle directly via `bd` CLI commands.
