"""Protocol conformance tests for bd-agent-chameleon extension points."""

from typing import Protocol, runtime_checkable

from pathlib import Path

from bd_agent_chameleon.beads_task_manager import BeadsTaskManager
from bd_agent_chameleon.claude_launcher import ClaudeLauncher
from bd_agent_chameleon.models import Role, Task, TaskStatus
from bd_agent_chameleon.protocols import SessionLauncher, TaskManager


@runtime_checkable
class _CheckableTaskManager(TaskManager, Protocol):
    """Runtime-checkable version of TaskManager for testing."""


@runtime_checkable
class _CheckableSessionLauncher(SessionLauncher, Protocol):
    """Runtime-checkable version of SessionLauncher for testing."""


class FakeTaskManager:
    """Minimal TaskManager implementation for conformance testing."""

    def poll(self, label: str) -> list[Task]:
        """Return an empty task list."""
        return []

    def claim(self, task_id: str) -> None:
        """No-op claim."""

    def complete(self, task_id: str) -> None:
        """No-op complete."""


class FakeSessionLauncher:
    """Minimal SessionLauncher implementation for conformance testing."""

    def launch(self, role: Role, task: Task) -> None:
        """No-op launch."""


class TestTaskManagerProtocol:
    """Tests for TaskManager protocol conformance."""

    def test_fake_satisfies_protocol(self) -> None:
        """A class with poll/claim/complete satisfies TaskManager."""
        mgr = FakeTaskManager()
        assert isinstance(mgr, _CheckableTaskManager)


class TestSessionLauncherProtocol:
    """Tests for SessionLauncher protocol conformance."""

    def test_fake_satisfies_protocol(self) -> None:
        """A class with launch() satisfies SessionLauncher."""
        launcher = FakeSessionLauncher()
        assert isinstance(launcher, _CheckableSessionLauncher)


class TestBeadsTaskManagerProtocol:
    """Tests for BeadsTaskManager protocol conformance."""

    def test_satisfies_protocol(self) -> None:
        """BeadsTaskManager satisfies the TaskManager protocol."""
        mgr = BeadsTaskManager(db_path=Path("/tmp/fake"))
        assert isinstance(mgr, _CheckableTaskManager)


class TestClaudeLauncherProtocol:
    """Tests for ClaudeLauncher protocol conformance."""

    def test_satisfies_protocol(self) -> None:
        """ClaudeLauncher satisfies the SessionLauncher protocol."""
        launcher = ClaudeLauncher()
        assert isinstance(launcher, _CheckableSessionLauncher)
