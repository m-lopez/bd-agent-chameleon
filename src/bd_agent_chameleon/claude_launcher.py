"""Concrete SessionLauncher that invokes the Claude CLI."""

import subprocess
import sys
import termios

from bd_agent_chameleon.models import Role, Task


class ClaudeLauncher:
    """Launches Claude CLI sessions with prompt composition and terminal management."""

    @staticmethod
    def _compose_prompt(role: Role, task: Task) -> str:
        """Combine role prompt with task content into a final prompt."""
        return f"{role.prompt}\n\n## Task: {task.title}\n\n{task.description}"

    @staticmethod
    def _build_command(prompt: str, role: Role) -> list[str]:
        """Build the Claude CLI command from a prompt and role configuration."""
        cmd: list[str] = ["claude", prompt]

        if not role.interactive:
            cmd.append("--print")

        if role.agent is not None:
            cmd.extend(["--agent", role.agent])

        return cmd

    @staticmethod
    def _launch_with_tty(cmd: list[str]) -> None:
        """Run a subprocess with terminal state save/restore."""
        saved_attrs: list = termios.tcgetattr(sys.stdin)  # type: ignore[type-arg]
        try:
            subprocess.run(cmd, check=False)
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, saved_attrs)

    def launch(self, role: Role, task: Task) -> None:
        """Launch a Claude session for the given role and task."""
        prompt: str = self._compose_prompt(role, task)
        cmd: list[str] = self._build_command(prompt, role)

        if sys.stdin.isatty():
            self._launch_with_tty(cmd)
        else:
            subprocess.run(cmd, check=False)
