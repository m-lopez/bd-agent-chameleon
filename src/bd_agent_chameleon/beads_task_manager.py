"""Concrete TaskManager implementation backed by the bd CLI."""

import json
import os
import subprocess
from typing import Any

from bd_agent_chameleon.models import Task, TaskStatus


def _parse_task(data: dict[str, Any]) -> Task:
    """Parse a bd JSON object into a Task."""
    return Task(
        id=data["id"],
        title=data["title"],
        description=data.get("description", ""),
        status=TaskStatus(data["status"]),
        labels=data.get("labels", []),
    )


class BeadsTaskManager:
    """Concrete TaskManager that shells out to the bd CLI."""

    def __init__(self) -> None:
        """Initialize and validate that BEADS_DIR is set."""
        beads_dir: str | None = os.environ.get("BEADS_DIR")
        if not beads_dir:
            msg = "BEADS_DIR environment variable is not set"
            raise RuntimeError(msg)

    def _run_bd(self, args: list[str]) -> Any:
        """Execute a bd CLI command and return parsed JSON output."""
        cmd: list[str] = ["bd", *args, "--json"]
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

