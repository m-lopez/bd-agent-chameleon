# Architecture

## Domain Model

bd-agent-chameleon is a runtime for agent orchestration. It polls a task management
system for work, claims tasks, and launches Claude sessions to execute them.
It is not an application framework — output contracts, DAG design, and
workflow logic are concerns of the flow authors building on top of this
runtime.

### Concepts

#### Role

Pure configuration that defines how a Claude session behaves.

| Field       | Type           | Description                                        |
|-------------|----------------|----------------------------------------------------|
| name        | `str`          | Unique identifier for the role.                    |
| agent       | `str \| None`  | Claude `--agent` flag. Optional.                   |
| prompt      | `str`          | Initial system prompt passed to Claude.            |
| interactive | `bool`         | If true, Claude runs interactively (no `--print`). |

A role maps 1:1 to a bd-agent-chameleon instance at runtime.

#### bd-agent-chameleon Instance

A running process loaded with a single role configuration.

- **One role per process.** Multi-role is achieved by running multiple
  bd-agent-chameleon processes, each with a different role.
- **Label filter** is derived from the role name (e.g., role name `reviewer`
  produces beads label `role-reviewer`).
- **Lifecycle states:** `polling` -> `executing` -> `polling` -> `shutdown`.

During `polling`, the instance queries the task management system for open
tasks matching its label filter. When a task is found, it transitions to
`executing`: it claims the task (marks it `in_progress`), launches Claude
with the role configuration, and on Claude exit marks the task `closed`.
It then returns to `polling`.

#### Task Management System

An external system that the runtime integrates with. Currently
[beads](https://github.com/steveyegge/beads).

The runtime requires only three operations from the task management system:

1. **poll** — list tasks matching a label with status `open`.
2. **claim** — set a task's status to `in_progress`.
3. **complete** — set a task's status to `closed`.

Everything else — task creation, prioritization, dependency management — is
handled by humans or higher-level tooling outside this runtime.

#### Task

A unit of work as seen by the runtime.

| Field       | Type                              | Description                                           |
|-------------|-----------------------------------|-------------------------------------------------------|
| id          | `str`                             | Unique identifier from the task system.               |
| title       | `str`                             | Short description of the work.                        |
| description | `str`                             | Detailed description of the work.                     |
| role label  | `str`                             | Matches a bd-agent-chameleon instance's label filter.  |
| status      | `open \| in_progress \| closed`   | Current lifecycle state.                              |

The runtime does not interpret priority, dependencies, or other
task-system-specific fields. Those are concerns of the flow authors.

#### Document Store

A shared filesystem where Claude sessions read from and write to.

The runtime imposes no structure on the document store. Flow authors
define their own conventions for organizing output artifacts.

#### Human Operator

A person who interacts with the system in two capacities:

- **Task creator** — authors tasks in the task management system with
  appropriate role labels. This happens outside the runtime.
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
   file? CLI flags? This determines how `bd-agent-chameleon --role reviewer`
   resolves the prompt, agent, and interactive settings.
2. **Task-to-prompt mapping** — when a task is claimed, what content is
   passed to Claude? The title? Description? Both? Prepended to the role's
   initial prompt? This is the seam between the runtime and flow authors.
3. **Beads integration surface** — should the runtime shell out to the `bd`
   CLI with `--json` output, or use a Python abstraction layer? An
   abstraction would make the task management system swappable.

## Component Architecture

### Overview

```
┌──────────────────────────────────────────────────────────┐
│                      CLI (typer)                         │
│           bd-agent-chameleon --role reviewer              │
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
└─────────┬──────────────┬───────────────────┬─────────────┘
          │              │                   │
          ▼              ▼                   ▼
┌────────────┐ ┌──────────────┐ ┌────────────────────┐
│TaskManager │ │ConfigManager │ │SessionLauncher     │
│«protocol»  │ │              │ │«protocol»          │
│            │ │- load_role() │ │                    │
│- poll()    │ │→ Role        │ │- launch(Role, Task)│
│- claim()   │ │              │ │                    │
│- complete()│ │              │ │                    │
└─────┬──────┘ └──────────────┘ └──────────┬─────────┘
      │ implements                         │ implements
      ▼                                    ▼
┌──────────────┐                  ┌─────────────────┐
│BeadsTaskMgr  │                  │ClaudeLauncher   │
└──────────────┘                  └─────────────────┘
```

### Components

#### Chameleon

The core orchestrator. Maps to the **bd-agent-chameleon Instance** in the domain
model. Receives all dependencies via constructor injection.

- Owns the state machine: `polling` → `executing` → `polling` → `shutdown`.
- During `polling`, calls `TaskManager.poll()` with the label filter
  derived from its Role.
- During `executing`, claims the task, delegates to SessionLauncher,
  then completes the task.
- Handles graceful shutdown (signals, quit key).

Chameleon contains no knowledge of how tasks are fetched, how config is
loaded, or how Claude is invoked. It only coordinates.

#### TaskManager (protocol)

Adapter interface to the external task management system. Maps to the
**Task Management System** in the domain model.

```
TaskManager
  poll(label: str) → list[Task]
  claim(task_id: str) → None
  complete(task_id: str) → None
```

`TaskManager` is a `typing.Protocol`. Concrete implementations speak
the external system's language. The first implementation is
`BeadsTaskManager`, which shells out to the `bd` CLI.

#### ConfigManager

Loads and provides Role configurations. Resolves a role name to a full
`Role` dataclass and derives the label filter.

```
ConfigManager
  load_role(name: str) → Role
```

The config source format (TOML, YAML, CLI flags) is an implementation
detail of ConfigManager. The rest of the system only sees `Role`.

#### SessionLauncher (protocol)

Builds and runs a Claude session. Maps to the subprocess management
concerns currently in `_build_claude_cmd` and `_launch_claude`.

```
SessionLauncher
  launch(role: Role, task: Task) → None
```

`SessionLauncher` is a `typing.Protocol`. The concrete implementation
is `ClaudeLauncher`, which:

- Composes the final prompt from `role.prompt` + `task.title` /
  `task.description`.
- Builds the Claude CLI invocation (`--print`, `--agent` flags).
- Manages terminal state (tty save/restore).
- Runs Claude as a subprocess.

SessionLauncher owns the **task-to-prompt mapping** — it decides how
Role and Task content combine into the Claude input.

### Data Types

| Type   | Kind      | Fields                                             |
|--------|-----------|----------------------------------------------------|
| `Role` | dataclass | `name`, `agent`, `prompt`, `interactive`, `label`  |
| `Task` | dataclass | `id`, `title`, `description`, `status`             |

`Role.label` is derived from `Role.name` (e.g., `"reviewer"` →
`"role-reviewer"`).

### Data Flow (Single Task Cycle)

```
Chameleon.run()
  │
  ├─ startup
  │   └─→ ConfigManager.load_role("reviewer") → Role
  │
  ├─ polling
  │   └─→ TaskManager.poll("role-reviewer") → [Task, ...]
  │
  ├─ executing
  │   ├─→ TaskManager.claim(task.id)
  │   ├─→ SessionLauncher.launch(role, task)
  │   │     ├─ compose prompt from role.prompt + task content
  │   │     ├─ build: claude <prompt> [--print] [--agent X]
  │   │     ├─ save/restore tty state
  │   │     └─ subprocess.run(...)
  │   └─→ TaskManager.complete(task.id)
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
   claimed, Chameleon passes both the `Role` and `Task` to
   `SessionLauncher.launch()`. The launcher decides how to combine
   `role.prompt` with `task.title`/`task.description` into the final
   Claude input. This keeps Chameleon free of prompt formatting concerns.

4. **ConfigManager is a concrete class.** Unlike TaskManager and
   SessionLauncher, there is no immediate need for multiple config
   backends. A protocol can be extracted later if needed.
