"""Core orchestrator that polls for tasks and launches Claude sessions."""

import logging
import time
from datetime import timedelta
from enum import StrEnum

from bd_agent_chameleon.config_manager import ConfigManager
from bd_agent_chameleon.models import (
    CHAMELEON_TASK_LABEL,
    Role,
    Task,
    extract_role_name,
)
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
        poll_interval: timedelta = timedelta(seconds=2),
    ) -> None:
        """Initialize with injected dependencies."""
        self._config_mgr: ConfigManager = config_mgr
        self._task_mgr: TaskManager = task_mgr
        self._launcher: SessionLauncher = launcher
        self._poll_interval: timedelta = poll_interval
        self._state: ChameleonState = ChameleonState.POLLING
        self._current_task: Task | None = None
        self._log: logging.Logger = logging.getLogger(__name__)

    def _poll(self) -> None:
        """Poll for chameleon tasks and transition to executing if found."""
        tasks: list[Task] = self._task_mgr.poll(CHAMELEON_TASK_LABEL)
        if tasks:
            self._current_task = tasks[0]
            self._state = ChameleonState.EXECUTING
        else:
            time.sleep(self._poll_interval.total_seconds())

    def _resolve_role(self, task: Task) -> Role | None:
        """Extract the role name from task labels and load its config."""
        role_name: str | None = extract_role_name(task.labels)
        if role_name is None:
            self._log.warning("Task %s has no role label", task.id)
            return None
        role: Role | None = self._config_mgr.load_role(role_name)
        if role is None:
            self._log.warning(
                "No config for role '%s' on task %s", role_name, task.id,
            )
        return role

    def _execute(self) -> None:
        """Resolve the role from task labels and launch a Claude session."""
        assert self._current_task is not None
        role: Role | None = self._resolve_role(self._current_task)
        self._launcher.launch(role, self._current_task)
        self._current_task = None
        self._state = ChameleonState.POLLING

    def run(self) -> None:
        """Run the main polling-executing loop until shutdown."""
        while self._state != ChameleonState.SHUTDOWN:
            if self._state == ChameleonState.POLLING:
                self._poll()
            elif self._state == ChameleonState.EXECUTING:
                self._execute()

    def shutdown(self) -> None:
        """Signal the chameleon to stop after the current cycle."""
        self._state = ChameleonState.SHUTDOWN
