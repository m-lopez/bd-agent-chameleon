"""Unit tests for BeadsTaskManager with mocked subprocess calls."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from bd_agent_chameleon.beads_task_manager import BeadsTaskManager
from bd_agent_chameleon.models import Task, TaskStatus

DB_PATH: Path = Path("/tmp/test-beads")


class TestPoll:
    """Tests for the poll method."""

    def test_returns_tasks_from_bd_list(self) -> None:
        """Poll parses bd list JSON into Task objects."""
        raw_json: str = json.dumps([
            {
                "id": "abc-1",
                "title": "Fix widget",
                "description": "The widget is broken",
                "status": "open",
            },
            {
                "id": "abc-2",
                "title": "Add feature",
                "description": "New feature needed",
                "status": "open",
            },
        ])
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=raw_json, stderr="",
        )
        with patch(
            "bd_agent_chameleon.beads_task_manager.subprocess.run",
            return_value=completed,
        ) as mock_run:
            mgr = BeadsTaskManager(db_path=DB_PATH)
            tasks: list[Task] = mgr.poll("role-reviewer")

        mock_run.assert_called_once()
        args: list[str] = mock_run.call_args[0][0]
        assert "list" in args
        assert "--label" in args
        assert "role-reviewer" in args
        assert "--json" in args

        assert len(tasks) == 2
        assert tasks[0] == Task(
            id="abc-1",
            title="Fix widget",
            description="The widget is broken",
            status=TaskStatus.OPEN,
        )

    def test_returns_empty_list_when_no_tasks(self) -> None:
        """Poll returns an empty list when bd list yields no results."""
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[]", stderr="",
        )
        with patch(
            "bd_agent_chameleon.beads_task_manager.subprocess.run",
            return_value=completed,
        ):
            mgr = BeadsTaskManager(db_path=DB_PATH)
            tasks: list[Task] = mgr.poll("role-writer")

        assert tasks == []

    def test_handles_missing_description(self) -> None:
        """Poll defaults description to empty string when absent."""
        raw_json: str = json.dumps([
            {"id": "x-1", "title": "No desc", "status": "open"},
        ])
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=raw_json, stderr="",
        )
        with patch(
            "bd_agent_chameleon.beads_task_manager.subprocess.run",
            return_value=completed,
        ):
            mgr = BeadsTaskManager(db_path=DB_PATH)
            tasks: list[Task] = mgr.poll("role-qa")

        assert tasks[0].description == ""


class TestClaim:
    """Tests for the claim method."""

    def test_calls_bd_update_with_claim_flag(self) -> None:
        """Claim invokes bd update with --claim for the given task id."""
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[]", stderr="",
        )
        with patch(
            "bd_agent_chameleon.beads_task_manager.subprocess.run",
            return_value=completed,
        ) as mock_run:
            mgr = BeadsTaskManager(db_path=DB_PATH)
            mgr.claim("abc-1")

        args: list[str] = mock_run.call_args[0][0]
        assert "update" in args
        assert "abc-1" in args
        assert "--claim" in args


class TestComplete:
    """Tests for the complete method."""

    def test_calls_bd_close(self) -> None:
        """Complete invokes bd close for the given task id."""
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="[]", stderr="",
        )
        with patch(
            "bd_agent_chameleon.beads_task_manager.subprocess.run",
            return_value=completed,
        ) as mock_run:
            mgr = BeadsTaskManager(db_path=DB_PATH)
            mgr.complete("abc-1")

        args: list[str] = mock_run.call_args[0][0]
        assert "close" in args
        assert "abc-1" in args


class TestErrorHandling:
    """Tests for error propagation from bd CLI failures."""

    def test_bd_failure_raises_called_process_error(self) -> None:
        """CalledProcessError propagates when bd exits non-zero."""
        with patch(
            "bd_agent_chameleon.beads_task_manager.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "bd"),
        ):
            mgr = BeadsTaskManager(db_path=DB_PATH)
            with pytest.raises(subprocess.CalledProcessError):
                mgr.poll("role-reviewer")
