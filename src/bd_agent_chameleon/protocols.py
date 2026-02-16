"""Protocol definitions for bd-agent-chameleon extension points."""

from typing import Protocol

from bd_agent_chameleon.models import Role, Task


class TaskManager(Protocol):
    """Abstraction for polling a task backend."""

    def poll(self, label: str) -> list[Task]: ...


class SessionLauncher(Protocol):
    """Abstraction for launching an interactive session."""

    def launch(self, role: Role | None, task: Task) -> None: ...
