"""Tests for Chameleon orchestrator."""

import logging
from datetime import timedelta

from bd_agent_chameleon.chameleon import Chameleon, ChameleonState
from bd_agent_chameleon.models import CHAMELEON_TASK_LABEL, Role, Task, TaskStatus


class FakeConfigManager:
    """Returns a fixed role or None."""

    def __init__(self, roles: dict[str, Role] | None = None) -> None:
        """Store the roles map."""
        self._roles: dict[str, Role] = roles or {}

    def load_role(self, name: str) -> Role | None:
        """Return the role for the given name, or None."""
        return self._roles.get(name)


class FakeTaskManager:
    """Returns canned poll results and records which label was polled."""

    def __init__(self, poll_results: list[list[Task]]) -> None:
        """Store the sequence of poll results to return."""
        self._poll_results: list[list[Task]] = list(poll_results)
        self.polled_labels: list[str] = []

    def poll(self, label: str) -> list[Task]:
        """Return the next canned result, or empty if exhausted."""
        self.polled_labels.append(label)
        if self._poll_results:
            return self._poll_results.pop(0)
        return []


class FakeLauncher:
    """Records launch calls."""

    def __init__(self) -> None:
        """Initialize the call log."""
        self.launches: list[tuple[Role | None, Task]] = []

    def launch(self, role: Role | None, task: Task) -> None:
        """Record the launch."""
        self.launches.append((role, task))


ROLE: Role = Role(name="reviewer", prompt="Review code.", interactive=False)
TASK: Task = Task(
    id="42",
    title="Fix bug",
    description="Fix the bug.",
    status=TaskStatus.OPEN,
    labels=["chameleon-task", "role-reviewer"],
)


class TestConstruction:
    """Tests for Chameleon initialization."""

    def test_initial_state_is_polling(self) -> None:
        """Chameleon starts in the polling state."""
        chameleon: Chameleon = Chameleon(
            FakeConfigManager(),
            FakeTaskManager([]),
            FakeLauncher(),
            timedelta(seconds=0),
        )
        assert chameleon._state == ChameleonState.POLLING

    def test_shutdown_sets_state(self) -> None:
        """shutdown() transitions state to SHUTDOWN."""
        chameleon: Chameleon = Chameleon(
            FakeConfigManager(),
            FakeTaskManager([]),
            FakeLauncher(),
            timedelta(seconds=0),
        )
        chameleon.shutdown()
        assert chameleon._state == ChameleonState.SHUTDOWN


class TestPolling:
    """Tests for Chameleon polling behavior."""

    def test_poll_uses_chameleon_task_label(self) -> None:
        """Chameleon polls with the fixed chameleon-task label."""
        task_mgr: FakeTaskManager = FakeTaskManager([[TASK]])
        launcher: FakeLauncher = FakeLauncher()
        chameleon: Chameleon = Chameleon(
            FakeConfigManager({"reviewer": ROLE}),
            task_mgr,
            launcher,
            timedelta(seconds=0),
        )
        original_execute = chameleon._execute

        def execute_then_stop() -> None:
            """Execute once then shut down."""
            original_execute()
            chameleon.shutdown()

        chameleon._execute = execute_then_stop  # type: ignore[assignment]
        chameleon.run()
        assert task_mgr.polled_labels == [CHAMELEON_TASK_LABEL]

    def test_empty_poll_stays_in_polling(self) -> None:
        """When no tasks are found, Chameleon stays in POLLING."""
        task_mgr: FakeTaskManager = FakeTaskManager([[], []])
        chameleon: Chameleon = Chameleon(
            FakeConfigManager(),
            task_mgr,
            FakeLauncher(),
            timedelta(seconds=0),
        )
        poll_count: int = 0
        original_poll = chameleon._poll

        def poll_then_stop() -> None:
            """Poll twice then shut down."""
            nonlocal poll_count
            original_poll()
            poll_count += 1
            if poll_count >= 2:
                chameleon.shutdown()

        chameleon._poll = poll_then_stop  # type: ignore[assignment]
        chameleon.run()
        assert poll_count == 2


class TestExecution:
    """Tests for Chameleon execution behavior."""

    def test_resolves_role_and_launches(self) -> None:
        """Chameleon resolves the role from task labels and launches with it."""
        task_mgr: FakeTaskManager = FakeTaskManager([[TASK]])
        launcher: FakeLauncher = FakeLauncher()
        chameleon: Chameleon = Chameleon(
            FakeConfigManager({"reviewer": ROLE}),
            task_mgr,
            launcher,
            timedelta(seconds=0),
        )
        original_execute = chameleon._execute

        def execute_then_stop() -> None:
            """Execute once then shut down."""
            original_execute()
            chameleon.shutdown()

        chameleon._execute = execute_then_stop  # type: ignore[assignment]
        chameleon.run()

        assert len(launcher.launches) == 1
        assert launcher.launches[0] == (ROLE, TASK)

    def test_no_role_label_launches_with_none(self, caplog: logging.LogRecord) -> None:
        """Task without role-* label launches with role=None and warns."""
        task_no_role: Task = Task(
            id="99",
            title="No role",
            description="No role label.",
            status=TaskStatus.OPEN,
            labels=["chameleon-task"],
        )
        task_mgr: FakeTaskManager = FakeTaskManager([[task_no_role]])
        launcher: FakeLauncher = FakeLauncher()
        chameleon: Chameleon = Chameleon(
            FakeConfigManager(),
            task_mgr,
            launcher,
            timedelta(seconds=0),
        )
        original_execute = chameleon._execute

        def execute_then_stop() -> None:
            """Execute once then shut down."""
            original_execute()
            chameleon.shutdown()

        chameleon._execute = execute_then_stop  # type: ignore[assignment]

        with caplog.at_level(logging.WARNING):
            chameleon.run()

        assert len(launcher.launches) == 1
        assert launcher.launches[0] == (None, task_no_role)
        assert "no role label" in caplog.text.lower()

    def test_missing_config_launches_with_none(self, caplog: logging.LogRecord) -> None:
        """Task with role label but missing config launches with role=None."""
        task_unknown: Task = Task(
            id="100",
            title="Unknown role",
            description="Unknown role.",
            status=TaskStatus.OPEN,
            labels=["chameleon-task", "role-unknown"],
        )
        task_mgr: FakeTaskManager = FakeTaskManager([[task_unknown]])
        launcher: FakeLauncher = FakeLauncher()
        chameleon: Chameleon = Chameleon(
            FakeConfigManager(),  # no roles configured
            task_mgr,
            launcher,
            timedelta(seconds=0),
        )
        original_execute = chameleon._execute

        def execute_then_stop() -> None:
            """Execute once then shut down."""
            original_execute()
            chameleon.shutdown()

        chameleon._execute = execute_then_stop  # type: ignore[assignment]

        with caplog.at_level(logging.WARNING):
            chameleon.run()

        assert len(launcher.launches) == 1
        assert launcher.launches[0] == (None, task_unknown)
        assert "no config for role" in caplog.text.lower()

    def test_returns_to_polling_after_execution(self) -> None:
        """Chameleon transitions back to POLLING after executing a task."""
        task_mgr: FakeTaskManager = FakeTaskManager([[TASK]])
        launcher: FakeLauncher = FakeLauncher()
        chameleon: Chameleon = Chameleon(
            FakeConfigManager({"reviewer": ROLE}),
            task_mgr,
            launcher,
            timedelta(seconds=0),
        )
        states_after_execute: list[ChameleonState] = []
        original_execute = chameleon._execute

        def execute_and_record() -> None:
            """Execute, record state, then shut down."""
            original_execute()
            states_after_execute.append(chameleon._state)
            chameleon.shutdown()

        chameleon._execute = execute_and_record  # type: ignore[assignment]
        chameleon.run()

        assert states_after_execute == [ChameleonState.POLLING]


class TestMultipleCycles:
    """Tests for Chameleon processing multiple tasks."""

    def test_processes_two_tasks(self) -> None:
        """Chameleon processes two tasks across multiple poll-execute cycles."""
        task_a: Task = Task(
            id="1",
            title="First",
            description="First task.",
            status=TaskStatus.OPEN,
            labels=["chameleon-task", "role-reviewer"],
        )
        task_b: Task = Task(
            id="2",
            title="Second",
            description="Second task.",
            status=TaskStatus.OPEN,
            labels=["chameleon-task", "role-reviewer"],
        )
        task_mgr: FakeTaskManager = FakeTaskManager([[task_a], [task_b]])
        launcher: FakeLauncher = FakeLauncher()
        chameleon: Chameleon = Chameleon(
            FakeConfigManager({"reviewer": ROLE}),
            task_mgr,
            launcher,
            timedelta(seconds=0),
        )
        execute_count: int = 0
        original_execute = chameleon._execute

        def count_and_stop() -> None:
            """Count executions and shut down after two."""
            nonlocal execute_count
            original_execute()
            execute_count += 1
            if execute_count >= 2:
                chameleon.shutdown()

        chameleon._execute = count_and_stop  # type: ignore[assignment]
        chameleon.run()

        assert len(launcher.launches) == 2


class TestRunOnce:
    """Tests for Chameleon one-shot execution."""

    def test_dispatches_task_when_found(self) -> None:
        """run_once() polls, finds a task, and launches it."""
        task_mgr: FakeTaskManager = FakeTaskManager([[TASK]])
        launcher: FakeLauncher = FakeLauncher()
        chameleon: Chameleon = Chameleon(
            FakeConfigManager({"reviewer": ROLE}),
            task_mgr,
            launcher,
            timedelta(seconds=0),
        )
        chameleon.run_once()

        assert len(launcher.launches) == 1
        assert launcher.launches[0] == (ROLE, TASK)

    def test_no_task_does_nothing(self) -> None:
        """run_once() returns immediately when no tasks are found."""
        task_mgr: FakeTaskManager = FakeTaskManager([[]])
        launcher: FakeLauncher = FakeLauncher()
        chameleon: Chameleon = Chameleon(
            FakeConfigManager(),
            task_mgr,
            launcher,
            timedelta(seconds=0),
        )
        chameleon.run_once()

        assert len(launcher.launches) == 0
        assert len(task_mgr.polled_labels) == 1

    def test_does_not_loop(self) -> None:
        """run_once() processes at most one task, even when multiple exist."""
        task_a: Task = Task(
            id="1", title="A", description="A.",
            status=TaskStatus.OPEN,
            labels=["chameleon-task", "role-reviewer"],
        )
        task_b: Task = Task(
            id="2", title="B", description="B.",
            status=TaskStatus.OPEN,
            labels=["chameleon-task", "role-reviewer"],
        )
        task_mgr: FakeTaskManager = FakeTaskManager([[task_a], [task_b]])
        launcher: FakeLauncher = FakeLauncher()
        chameleon: Chameleon = Chameleon(
            FakeConfigManager({"reviewer": ROLE}),
            task_mgr,
            launcher,
            timedelta(seconds=0),
        )
        chameleon.run_once()

        assert len(launcher.launches) == 1
        assert len(task_mgr.polled_labels) == 1


class TestShutdown:
    """Tests for Chameleon shutdown behavior."""

    def test_shutdown_exits_run_loop(self) -> None:
        """Calling shutdown() causes run() to exit."""
        chameleon: Chameleon = Chameleon(
            FakeConfigManager(),
            FakeTaskManager([]),
            FakeLauncher(),
            timedelta(seconds=0),
        )
        original_poll = chameleon._poll

        def poll_then_stop() -> None:
            """Poll once then shut down."""
            original_poll()
            chameleon.shutdown()

        chameleon._poll = poll_then_stop  # type: ignore[assignment]
        chameleon.run()

        assert chameleon._state == ChameleonState.SHUTDOWN
