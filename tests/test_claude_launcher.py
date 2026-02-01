"""Tests for ClaudeLauncher."""

from unittest.mock import MagicMock, patch

from bd_agent_chameleon.claude_launcher import ClaudeLauncher
from bd_agent_chameleon.models import Role, Task, TaskStatus


class TestComposePrompt:
    """Tests for ClaudeLauncher._compose_prompt."""

    def test_combines_role_prompt_with_task(self) -> None:
        """Prompt contains the role prompt, task title, and task description."""
        role: Role = Role(
            name="reviewer", prompt="Review the code.", interactive=False
        )
        task: Task = Task(
            id="1",
            title="Fix the bug",
            description="There is a bug in foo.py.",
            status=TaskStatus.OPEN,
        )
        result: str = ClaudeLauncher._compose_prompt(role, task)

        assert "Review the code." in result
        assert "Fix the bug" in result
        assert "There is a bug in foo.py." in result

    def test_prompt_structure(self) -> None:
        """Prompt follows the expected structure: role prompt, then task heading, then description."""
        role: Role = Role(name="coder", prompt="Write code.", interactive=False)
        task: Task = Task(
            id="2",
            title="Add feature",
            description="Add the frobnicate feature.",
            status=TaskStatus.OPEN,
        )
        result: str = ClaudeLauncher._compose_prompt(role, task)

        assert (
            result
            == "Write code.\n\n## Task: Add feature\n\nAdd the frobnicate feature."
        )


class TestBuildCommand:
    """Tests for ClaudeLauncher._build_command."""

    def test_non_interactive_includes_print_flag(self) -> None:
        """Non-interactive roles produce a command with --print."""
        role: Role = Role(name="reviewer", prompt="Review.", interactive=False)
        cmd: list[str] = ClaudeLauncher._build_command("the prompt", role)

        assert cmd[0] == "claude"
        assert cmd[1] == "the prompt"
        assert "--print" in cmd

    def test_interactive_omits_print_flag(self) -> None:
        """Interactive roles produce a command without --print."""
        role: Role = Role(name="writer", prompt="Write.", interactive=True)
        cmd: list[str] = ClaudeLauncher._build_command("the prompt", role)

        assert "--print" not in cmd

    def test_agent_flag_included_when_set(self) -> None:
        """Roles with an agent produce a command with --agent."""
        role: Role = Role(
            name="coder", prompt="Code.", interactive=False, agent="my-agent"
        )
        cmd: list[str] = ClaudeLauncher._build_command("the prompt", role)

        assert "--agent" in cmd
        agent_idx: int = cmd.index("--agent")
        assert cmd[agent_idx + 1] == "my-agent"

    def test_agent_flag_omitted_when_none(self) -> None:
        """Roles without an agent produce a command without --agent."""
        role: Role = Role(name="coder", prompt="Code.", interactive=False)
        cmd: list[str] = ClaudeLauncher._build_command("the prompt", role)

        assert "--agent" not in cmd


class TestLaunch:
    """Tests for ClaudeLauncher.launch."""

    @patch("bd_agent_chameleon.claude_launcher.subprocess.run")
    @patch("bd_agent_chameleon.claude_launcher.sys.stdin")
    def test_launch_calls_subprocess(
        self, mock_stdin: MagicMock, mock_run: MagicMock
    ) -> None:
        """launch() invokes subprocess.run with the built command."""
        mock_stdin.isatty.return_value = False
        role: Role = Role(name="reviewer", prompt="Review.", interactive=False)
        task: Task = Task(
            id="1", title="Fix bug", description="Details.", status=TaskStatus.OPEN
        )

        ClaudeLauncher().launch(role, task)

        mock_run.assert_called_once()
        cmd: list[str] = mock_run.call_args[0][0]
        assert cmd[0] == "claude"
        assert "--print" in cmd

    @patch("bd_agent_chameleon.claude_launcher.subprocess.run")
    @patch("bd_agent_chameleon.claude_launcher.sys.stdin")
    def test_launch_interactive_omits_print(
        self, mock_stdin: MagicMock, mock_run: MagicMock
    ) -> None:
        """launch() omits --print for interactive roles."""
        mock_stdin.isatty.return_value = False
        role: Role = Role(name="writer", prompt="Write.", interactive=True)
        task: Task = Task(
            id="2",
            title="Write docs",
            description="Details.",
            status=TaskStatus.OPEN,
        )

        ClaudeLauncher().launch(role, task)

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
        task: Task = Task(
            id="1", title="Fix bug", description="Details.", status=TaskStatus.OPEN
        )

        ClaudeLauncher().launch(role, task)

        mock_tcgetattr.assert_called_once_with(mock_stdin)
        mock_tcsetattr.assert_called_once()
        mock_run.assert_called_once()
