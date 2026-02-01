"""Tests for Chameleon orchestrator."""

from datetime import timedelta

from bd_agent_chameleon.chameleon import Chameleon, ChameleonState
from bd_agent_chameleon.models import Role, Task, TaskStatus


class FakeConfigManager:
    """Returns a fixed role."""

    def __init__(self, role: Role) -> None:
        """Store the role to return."""
        self._role: Role = role

    def load_role(self, name: str) -> Role:
        """Return the stored role."""
        return self._role


class FakeTaskManager:
    """Returns canned poll results and records claim/complete calls."""

    def __init__(self, poll_results: list[list[Task]]) -> None:
        """Store the sequence of poll results to return."""
        self._poll_results: list[list[Task]] = list(poll_results)
        self.claimed: list[str] = []
        self.completed: list[str] = []

    def poll(self, label: str) -> list[Task]:
        """Return the next canned result, or empty if exhausted."""
        if self._poll_results:
            return self._poll_results.pop(0)
        return []

    def claim(self, task_id: str) -> None:
        """Record the claim."""
        self.claimed.append(task_id)

    def complete(self, task_id: str) -> None:
        """Record the completion."""
        self.completed.append(task_id)


class FakeLauncher:
    """Records launch calls."""

    def __init__(self) -> None:
        """Initialize the call log."""
        self.launches: list[tuple[Role, Task]] = []

    def launch(self, role: Role, task: Task) -> None:
        """Record the launch."""
        self.launches.append((role, task))


ROLE: Role = Role(name="reviewer", prompt="Review code.", interactive=False)
TASK: Task = Task(
    id="42",
    title="Fix bug",
    description="Fix the bug.",
    status=TaskStatus.OPEN,
)


class TestConstruction:
    """Tests for Chameleon initialization."""

    def test_initial_state_is_polling(self) -> None:
        """Chameleon starts in the polling state."""
        chameleon: Chameleon = Chameleon(
            FakeConfigManager(ROLE),
            FakeTaskManager([]),
            FakeLauncher(),
            "reviewer",
            timedelta(seconds=0),
        )
        assert chameleon._state == ChameleonState.POLLING

    def test_shutdown_sets_state(self) -> None:
        """shutdown() transitions state to SHUTDOWN."""
        chameleon: Chameleon = Chameleon(
            FakeConfigManager(ROLE),
            FakeTaskManager([]),
            FakeLauncher(),
            "reviewer",
            timedelta(seconds=0),
        )
        chameleon.shutdown()
        assert chameleon._state == ChameleonState.SHUTDOWN


class TestPolling:
    """Tests for Chameleon polling behavior."""

    def test_poll_uses_role_label(self) -> None:
        """Chameleon polls with the label derived from the role name."""
        task_mgr: FakeTaskManager = FakeTaskManager([[TASK]])
        launcher: FakeLauncher = FakeLauncher()
        chameleon: Chameleon = Chameleon(
            FakeConfigManager(ROLE),
            task_mgr,
            launcher,
            "reviewer",
            timedelta(seconds=0),
        )
        original_execute = chameleon._execute

        def execute_then_stop(role: Role) -> None:
            """Execute once then shut down."""
            original_execute(role)
            chameleon.shutdown()

        chameleon._execute = execute_then_stop  # type: ignore[assignment]
        chameleon.run()
        assert task_mgr.claimed == ["42"]

    def test_empty_poll_stays_in_polling(self) -> None:
        """When no tasks are found, Chameleon stays in POLLING."""
        task_mgr: FakeTaskManager = FakeTaskManager([[], []])
        chameleon: Chameleon = Chameleon(
            FakeConfigManager(ROLE),
            task_mgr,
            FakeLauncher(),
            "reviewer",
            timedelta(seconds=0),
        )
        poll_count: int = 0
        original_poll = chameleon._poll

        def poll_then_stop(role: Role) -> None:
            """Poll twice then shut down."""
            nonlocal poll_count
            original_poll(role)
            poll_count += 1
            if poll_count >= 2:
                chameleon.shutdown()

        chameleon._poll = poll_then_stop  # type: ignore[assignment]
        chameleon.run()
        assert poll_count == 2
        assert task_mgr.claimed == []


class TestExecution:
    """Tests for Chameleon execution behavior."""

    def test_claims_launches_and_completes(self) -> None:
        """Chameleon claims the task, launches a session, and completes the task."""
        task_mgr: FakeTaskManager = FakeTaskManager([[TASK]])
        launcher: FakeLauncher = FakeLauncher()
        chameleon: Chameleon = Chameleon(
            FakeConfigManager(ROLE),
            task_mgr,
            launcher,
            "reviewer",
            timedelta(seconds=0),
        )
        original_execute = chameleon._execute

        def execute_then_stop(role: Role) -> None:
            """Execute once then shut down."""
            original_execute(role)
            chameleon.shutdown()

        chameleon._execute = execute_then_stop  # type: ignore[assignment]
        chameleon.run()

        assert task_mgr.claimed == ["42"]
        assert task_mgr.completed == ["42"]
        assert len(launcher.launches) == 1
        assert launcher.launches[0] == (ROLE, TASK)

    def test_returns_to_polling_after_execution(self) -> None:
        """Chameleon transitions back to POLLING after executing a task."""
        task_mgr: FakeTaskManager = FakeTaskManager([[TASK]])
        launcher: FakeLauncher = FakeLauncher()
        chameleon: Chameleon = Chameleon(
            FakeConfigManager(ROLE),
            task_mgr,
            launcher,
            "reviewer",
            timedelta(seconds=0),
        )
        states_after_execute: list[ChameleonState] = []
        original_execute = chameleon._execute

        def execute_and_record(role: Role) -> None:
            """Execute, record state, then shut down."""
            original_execute(role)
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
        )
        task_b: Task = Task(
            id="2",
            title="Second",
            description="Second task.",
            status=TaskStatus.OPEN,
        )
        task_mgr: FakeTaskManager = FakeTaskManager([[task_a], [task_b]])
        launcher: FakeLauncher = FakeLauncher()
        chameleon: Chameleon = Chameleon(
            FakeConfigManager(ROLE),
            task_mgr,
            launcher,
            "reviewer",
            timedelta(seconds=0),
        )
        execute_count: int = 0
        original_execute = chameleon._execute

        def count_and_stop(role: Role) -> None:
            """Count executions and shut down after two."""
            nonlocal execute_count
            original_execute(role)
            execute_count += 1
            if execute_count >= 2:
                chameleon.shutdown()

        chameleon._execute = count_and_stop  # type: ignore[assignment]
        chameleon.run()

        assert task_mgr.claimed == ["1", "2"]
        assert task_mgr.completed == ["1", "2"]
        assert len(launcher.launches) == 2


class TestShutdown:
    """Tests for Chameleon shutdown behavior."""

    def test_shutdown_exits_run_loop(self) -> None:
        """Calling shutdown() causes run() to exit."""
        chameleon: Chameleon = Chameleon(
            FakeConfigManager(ROLE),
            FakeTaskManager([]),
            FakeLauncher(),
            "reviewer",
            timedelta(seconds=0),
        )
        original_poll = chameleon._poll

        def poll_then_stop(role: Role) -> None:
            """Poll once then shut down."""
            original_poll(role)
            chameleon.shutdown()

        chameleon._poll = poll_then_stop  # type: ignore[assignment]
        chameleon.run()

        assert chameleon._state == ChameleonState.SHUTDOWN
