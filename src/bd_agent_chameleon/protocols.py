"""Protocol definitions for bd-agent-chameleon extension points."""

from typing import Protocol

from bd_agent_chameleon.models import Role, Task


class TaskManager(Protocol):
    """Adapter interface to an external task management system."""

    def poll(self, label: str) -> list[Task]:
        """List tasks matching a label with status open."""
        ...

    def claim(self, task_id: str) -> None:
        """Set a task's status to in_progress."""
        ...

    def complete(self, task_id: str) -> None:
        """Set a task's status to closed."""
        ...


class SessionLauncher(Protocol):
    """Builds and runs a Claude session."""

    def launch(self, role: Role, task: Task) -> None:
        """Launch a Claude session for the given role and task."""
        ...
