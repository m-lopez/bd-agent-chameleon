"""Concrete SessionLauncher that invokes the Claude CLI."""

import subprocess
import sys
import termios
from pathlib import Path

from bd_agent_chameleon.models import Role, Task

_WORKFLOW_TEMPLATE: str = """
Use this workflow to execute the task in the ticket:
  - Read the ticket using: `bd show {ticket_id}`
  - Claim the ticket using: `bd update {ticket_id} --claim`
  - Do the work described in the ticket
  - Then close the ticket using: `bd close {ticket_id}`"""


class ClaudeLauncher:
    """Launches Claude CLI sessions with prompt composition and terminal management."""

    def __init__(self, cwd: Path) -> None:
        """Initialize with the working directory for spawned sessions."""
        self._cwd: Path = cwd

    @staticmethod
    def _compose_prompt(role: Role | None, task: Task) -> str:
        """Combine optional role context with workflow instructions."""
        parts: list[str] = []
        if role is not None:
            parts.append(role.prompt)
        parts.append(_WORKFLOW_TEMPLATE.format(ticket_id=task.id))
        return "\n".join(parts)

    @staticmethod
    def _build_command(prompt: str, role: Role | None) -> list[str]:
        """Build the Claude CLI command from a prompt and optional role."""
        cmd: list[str] = ["claude", prompt]

        if role is not None and not role.interactive:
            cmd.extend([
                "--print", "--verbose",
                "--output-format", "stream-json",
                "--permission-mode", "bypassPermissions",
            ])

        if role is not None:
            cmd.extend(["--agent", role.name])

        return cmd

    @staticmethod
    def _launch_with_tty(cmd: list[str], cwd: Path) -> None:
        """Run a subprocess with terminal state save/restore."""
        saved_attrs: list = termios.tcgetattr(sys.stdin)  # type: ignore[type-arg]
        try:
            subprocess.run(cmd, cwd=cwd, check=False)
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, saved_attrs)

    def launch(self, role: Role | None, task: Task) -> None:
        """Launch a Claude session for the given task and optional role."""
        prompt: str = self._compose_prompt(role, task)
        cmd: list[str] = self._build_command(prompt, role)

        if sys.stdin.isatty():
            self._launch_with_tty(cmd, self._cwd)
        else:
            subprocess.run(cmd, cwd=self._cwd, check=False)
