"""Concrete TaskManager implementation backed by the bd CLI."""

import json
import subprocess
from pathlib import Path
from typing import Any

from bd_agent_chameleon.models import Task, TaskStatus


def _parse_task(data: dict[str, Any]) -> Task:
    """Parse a bd JSON object into a Task."""
    return Task(
        id=data["id"],
        title=data["title"],
        description=data.get("description", ""),
        status=TaskStatus(data["status"]),
    )


class BeadsTaskManager:
    """Concrete TaskManager that shells out to the bd CLI."""

    def __init__(self, db_path: Path) -> None:
        """Initialize with the path to the beads database directory."""
        self._db_path: Path = db_path

    def _run_bd(self, args: list[str]) -> Any:
        """Execute a bd CLI command and return parsed JSON output."""
        cmd: list[str] = [
            "bd", *args,
            "--json",
            "--db", str(self._db_path),
        ]
        result: subprocess.CompletedProcess[str] = subprocess.run(
            cmd, capture_output=True, check=True, text=True,
        )
        return json.loads(result.stdout)

    def poll(self, label: str) -> list[Task]:
        """List open tasks matching the given label."""
        raw: list[dict[str, Any]] = self._run_bd(
            ["list", "--label", label],
        )
        return [_parse_task(entry) for entry in raw]

    def claim(self, task_id: str) -> None:
        """Claim a task by setting its status to in_progress."""
        self._run_bd(["update", task_id, "--claim"])

    def complete(self, task_id: str) -> None:
        """Complete a task by closing it."""
        self._run_bd(["close", task_id])
