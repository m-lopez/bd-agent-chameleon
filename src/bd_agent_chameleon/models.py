"""Domain data types for bd-agent-chameleon."""

from dataclasses import dataclass
from enum import StrEnum

ROLE_LABEL_PREFIX: str = "role-"


class TaskStatus(StrEnum):
    """Lifecycle states for a task."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


@dataclass(frozen=True)
class Task:
    """A unit of work as seen by the runtime."""

    id: str
    title: str
    description: str
    status: TaskStatus


@dataclass(frozen=True)
class Role:
    """Configuration that defines how a Claude session behaves."""

    name: str
    prompt: str
    interactive: bool
    agent: str | None = None
    label: str = ""

    def __post_init__(self) -> None:
        """Derive label from name if not explicitly set."""
        if not self.label:
            object.__setattr__(self, "label", f"{ROLE_LABEL_PREFIX}{self.name}")
