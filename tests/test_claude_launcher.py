"""Tests for ClaudeLauncher."""

from unittest.mock import MagicMock, patch

from bd_agent_chameleon.claude_launcher import ClaudeLauncher, _WORKFLOW_TEMPLATE
from bd_agent_chameleon.models import Role, Task, TaskStatus


TASK: Task = Task(
    id="42",
    title="Fix the bug",
    description="There is a bug in foo.py.",
    status=TaskStatus.OPEN,
    labels=["chameleon-task", "role-reviewer"],
)


class TestComposePrompt:
    """Tests for ClaudeLauncher._compose_prompt."""

    def test_with_role(self) -> None:
        """Prompt contains the role prompt followed by workflow template."""
        role: Role = Role(
            name="reviewer", prompt="Review the code.", interactive=False,
        )
        result: str = ClaudeLauncher._compose_prompt(role, TASK)

        assert result.startswith("Review the code.")
        assert "bd show 42" in result
        assert "bd update 42 --claim" in result
        assert "bd close 42" in result

    def test_without_role(self) -> None:
        """Prompt contains only the workflow template when role is None."""
        result: str = ClaudeLauncher._compose_prompt(None, TASK)

        assert "Review the code." not in result
        assert "bd show 42" in result
        assert "bd update 42 --claim" in result
        assert "bd close 42" in result

    def test_workflow_template_includes_ticket_id(self) -> None:
        """Workflow template is formatted with the task's ticket ID."""
        result: str = ClaudeLauncher._compose_prompt(None, TASK)

        assert "42" in result


class TestBuildCommand:
    """Tests for ClaudeLauncher._build_command."""

    def test_with_role_non_interactive(self) -> None:
        """Non-interactive role produces --print and --agent flags."""
        role: Role = Role(name="reviewer", prompt="Review.", interactive=False)
        cmd: list[str] = ClaudeLauncher._build_command("the prompt", role)

        assert cmd[0] == "claude"
        assert cmd[1] == "the prompt"
        assert "--print" in cmd
        assert "--agent" in cmd
        agent_idx: int = cmd.index("--agent")
        assert cmd[agent_idx + 1] == "reviewer"

    def test_with_role_interactive(self) -> None:
        """Interactive role omits --print but includes --agent."""
        role: Role = Role(name="writer", prompt="Write.", interactive=True)
        cmd: list[str] = ClaudeLauncher._build_command("the prompt", role)

        assert "--print" not in cmd
        assert "--agent" in cmd
        agent_idx: int = cmd.index("--agent")
        assert cmd[agent_idx + 1] == "writer"

    def test_without_role(self) -> None:
        """None role produces no --print and no --agent."""
        cmd: list[str] = ClaudeLauncher._build_command("the prompt", None)

        assert cmd == ["claude", "the prompt"]


class TestLaunch:
    """Tests for ClaudeLauncher.launch."""

    @patch("bd_agent_chameleon.claude_launcher.subprocess.run")
    @patch("bd_agent_chameleon.claude_launcher.sys.stdin")
    def test_launch_with_role(
        self, mock_stdin: MagicMock, mock_run: MagicMock
    ) -> None:
        """launch() invokes subprocess.run with the built command."""
        mock_stdin.isatty.return_value = False
        role: Role = Role(name="reviewer", prompt="Review.", interactive=False)

        ClaudeLauncher().launch(role, TASK)

        mock_run.assert_called_once()
        cmd: list[str] = mock_run.call_args[0][0]
        assert cmd[0] == "claude"
        assert "--print" in cmd
        assert "--agent" in cmd

    @patch("bd_agent_chameleon.claude_launcher.subprocess.run")
    @patch("bd_agent_chameleon.claude_launcher.sys.stdin")
    def test_launch_without_role(
        self, mock_stdin: MagicMock, mock_run: MagicMock
    ) -> None:
        """launch() works with role=None."""
        mock_stdin.isatty.return_value = False

        ClaudeLauncher().launch(None, TASK)

        mock_run.assert_called_once()
        cmd: list[str] = mock_run.call_args[0][0]
        assert cmd[0] == "claude"
        assert "--print" not in cmd
        assert "--agent" not in cmd

    @patch("bd_agent_chameleon.claude_launcher.subprocess.run")
    @patch("bd_agent_chameleon.claude_launcher.sys.stdin")
    def test_launch_interactive_omits_print(
        self, mock_stdin: MagicMock, mock_run: MagicMock
    ) -> None:
        """launch() omits --print for interactive roles."""
        mock_stdin.isatty.return_value = False
        role: Role = Role(name="writer", prompt="Write.", interactive=True)

        ClaudeLauncher().launch(role, TASK)

        cmd: list[str] = mock_run.call_args[0][0]
        assert "--print" not in cmd

    @patch("bd_agent_chameleon.claude_launcher.subprocess.run")
    @patch("bd_agent_chameleon.claude_launcher.termios.tcsetattr")
    @patch("bd_agent_chameleon.claude_launcher.termios.tcgetattr")
    @patch("bd_agent_chameleon.claude_launcher.sys.stdin")
    def test_launch_saves_and_restores_tty(
        self,
        mock_stdin: MagicMock,
        mock_tcgetattr: MagicMock,
        mock_tcsetattr: MagicMock,
        mock_run: MagicMock,
    ) -> None:
        """launch() saves and restores terminal state when stdin is a tty."""
        mock_stdin.isatty.return_value = True
        saved_attrs: list = [1, 2, 3]
        mock_tcgetattr.return_value = saved_attrs

        role: Role = Role(name="reviewer", prompt="Review.", interactive=False)

        ClaudeLauncher().launch(role, TASK)

        mock_tcgetattr.assert_called_once_with(mock_stdin)
        mock_tcsetattr.assert_called_once()
        mock_run.assert_called_once()
