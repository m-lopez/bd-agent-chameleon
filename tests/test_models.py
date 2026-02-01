"""Unit tests for bd-agent-chameleon domain data types."""

import pytest

from bd_agent_chameleon.models import Role, Task, TaskStatus


class TestTask:
    """Tests for the Task dataclass."""

    def test_construction(self) -> None:
        """Task stores all fields correctly."""
        task = Task(
            id="abc-123",
            title="Fix the widget",
            description="The widget is broken",
            status=TaskStatus.OPEN,
        )
        assert task.id == "abc-123"
        assert task.title == "Fix the widget"
        assert task.description == "The widget is broken"
        assert task.status == TaskStatus.OPEN

    def test_status_is_string(self) -> None:
        """TaskStatus values compare equal to their string form."""
        task = Task(
            id="1",
            title="t",
            description="d",
            status=TaskStatus.IN_PROGRESS,
        )
        assert task.status == "in_progress"

    def test_frozen(self) -> None:
        """Task instances are immutable."""
        task = Task(id="1", title="t", description="d", status=TaskStatus.OPEN)
        with pytest.raises(AttributeError):
            task.id = "2"  # type: ignore[misc]


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
        assert role.agent is None

    def test_label_derived_from_name(self) -> None:
        """Label is auto-derived as 'role-{name}'."""
        role = Role(name="reviewer", prompt="p", interactive=False)
        assert role.label == "role-reviewer"

    def test_label_with_different_names(self) -> None:
        """Label derivation works for various role names."""
        assert Role(name="writer", prompt="p", interactive=True).label == "role-writer"
        assert Role(name="qa", prompt="p", interactive=False).label == "role-qa"

    def test_agent_optional(self) -> None:
        """Agent field can be set explicitly."""
        role = Role(
            name="coder",
            prompt="Write code",
            interactive=False,
            agent="my-agent",
        )
        assert role.agent == "my-agent"

    def test_frozen(self) -> None:
        """Role instances are immutable."""
        role = Role(name="r", prompt="p", interactive=False)
        with pytest.raises(AttributeError):
            role.name = "x"  # type: ignore[misc]
