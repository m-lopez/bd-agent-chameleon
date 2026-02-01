"""Core orchestrator that coordinates task polling, claiming, and session launching."""

import time
from datetime import timedelta
from enum import StrEnum

from bd_agent_chameleon.config_manager import ConfigManager
from bd_agent_chameleon.models import Role, Task
from bd_agent_chameleon.protocols import SessionLauncher, TaskManager


class ChameleonState(StrEnum):
    """Lifecycle states for a Chameleon instance."""

    POLLING = "polling"
    EXECUTING = "executing"
    SHUTDOWN = "shutdown"


class Chameleon:
    """Orchestrator that polls for tasks and launches Claude sessions."""

    def __init__(
        self,
        config_mgr: ConfigManager,
        task_mgr: TaskManager,
        launcher: SessionLauncher,
        role_name: str,
        poll_interval: timedelta = timedelta(seconds=2),
    ) -> None:
        """Initialize with injected dependencies and role configuration."""
        self._config_mgr: ConfigManager = config_mgr
        self._task_mgr: TaskManager = task_mgr
        self._launcher: SessionLauncher = launcher
        self._role_name: str = role_name
        self._poll_interval: timedelta = poll_interval
        self._state: ChameleonState = ChameleonState.POLLING
        self._current_task: Task | None = None

    def _poll(self, role: Role) -> None:
        """Poll for open tasks and transition to executing if one is found."""
        tasks: list[Task] = self._task_mgr.poll(role.label)
        if tasks:
            self._current_task = tasks[0]
            self._state = ChameleonState.EXECUTING
        else:
            time.sleep(self._poll_interval.total_seconds())

    def _execute(self, role: Role) -> None:
        """Claim the current task, launch a session, and mark it complete."""
        assert self._current_task is not None
        self._task_mgr.claim(self._current_task.id)
        self._launcher.launch(role, self._current_task)
        self._task_mgr.complete(self._current_task.id)
        self._current_task = None
        self._state = ChameleonState.POLLING

    def run(self) -> None:
        """Run the main polling-executing loop until shutdown."""
        role: Role = self._config_mgr.load_role(self._role_name)
        while self._state != ChameleonState.SHUTDOWN:
            if self._state == ChameleonState.POLLING:
                self._poll(role)
            elif self._state == ChameleonState.EXECUTING:
                self._execute(role)

    def shutdown(self) -> None:
        """Signal the chameleon to stop after the current cycle."""
        self._state = ChameleonState.SHUTDOWN
