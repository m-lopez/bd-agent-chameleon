"""Domain data types for bd-agent-chameleon."""

from dataclasses import dataclass
from enum import StrEnum

ROLE_LABEL_PREFIX: str = "role-"
CHAMELEON_TASK_LABEL: str = "chameleon-task"


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
    labels: list[str]


def extract_role_name(labels: list[str]) -> str | None:
    """Return the role name from the first role-* label, or None."""
    for label in labels:
        if label.startswith(ROLE_LABEL_PREFIX):
            return label[len(ROLE_LABEL_PREFIX):]
    return None


@dataclass(frozen=True)
class Role:
    """Configuration that defines how a Claude session behaves."""

    name: str
    prompt: str
    interactive: bool
