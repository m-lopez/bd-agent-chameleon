"""Unit tests for bd-agent-chameleon domain data types."""

import pytest

from bd_agent_chameleon.models import (
    CHAMELEON_TASK_LABEL,
    Role,
    Task,
    TaskStatus,
    extract_role_name,
)


class TestTask:
    """Tests for the Task dataclass."""

    def test_construction(self) -> None:
        """Task stores all fields correctly."""
        task = Task(
            id="abc-123",
            title="Fix the widget",
            description="The widget is broken",
            status=TaskStatus.OPEN,
            labels=["chameleon-task", "role-reviewer"],
        )
        assert task.id == "abc-123"
        assert task.title == "Fix the widget"
        assert task.description == "The widget is broken"
        assert task.status == TaskStatus.OPEN
        assert task.labels == ["chameleon-task", "role-reviewer"]

    def test_status_is_string(self) -> None:
        """TaskStatus values compare equal to their string form."""
        task = Task(
            id="1",
            title="t",
            description="d",
            status=TaskStatus.IN_PROGRESS,
            labels=[],
        )
        assert task.status == "in_progress"

    def test_frozen(self) -> None:
        """Task instances are immutable."""
        task = Task(
            id="1", title="t", description="d",
            status=TaskStatus.OPEN, labels=[],
        )
        with pytest.raises(AttributeError):
            task.id = "2"  # type: ignore[misc]


class TestExtractRoleName:
    """Tests for extract_role_name helper."""

    def test_extracts_role_from_label(self) -> None:
        """Returns the role name from a role-* label."""
        assert extract_role_name(["chameleon-task", "role-reviewer"]) == "reviewer"

    def test_returns_none_when_no_role_label(self) -> None:
        """Returns None when no role-* label is present."""
        assert extract_role_name(["chameleon-task", "priority-high"]) is None

    def test_first_role_label_wins(self) -> None:
        """Returns the first role-* label when multiple are present."""
        assert extract_role_name(["role-writer", "role-reviewer"]) == "writer"

    def test_empty_labels(self) -> None:
        """Returns None for an empty labels list."""
        assert extract_role_name([]) is None


class TestChameleonTaskLabel:
    """Tests for the CHAMELEON_TASK_LABEL constant."""

    def test_value(self) -> None:
        """Constant has the expected value."""
        assert CHAMELEON_TASK_LABEL == "chameleon-task"


class TestRole:
    """Tests for the Role dataclass."""

    def test_construction(self) -> None:
        """Role stores all fields correctly."""
        role = Role(
            name="reviewer",
            prompt="Review the code",
            interactive=False,
        )
        assert role.name == "reviewer"
        assert role.prompt == "Review the code"
        assert role.interactive is False

    def test_frozen(self) -> None:
        """Role instances are immutable."""
        role = Role(name="r", prompt="p", interactive=False)
        with pytest.raises(AttributeError):
            role.name = "x"  # type: ignore[misc]
