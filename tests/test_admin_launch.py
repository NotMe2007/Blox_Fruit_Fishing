"""Elevation checks are mocked: these tests never display UAC."""
import ctypes
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest
import Admin_Launch as admin


@pytest.fixture
def shell(monkeypatch):
    api = Mock()
    api.IsUserAnAdmin.return_value = False
    api.ShellExecuteW.return_value = 33
    monkeypatch.setattr(ctypes.windll, "shell32", api)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    return api


def test_already_elevated_does_not_relaunch(shell):
    shell.IsUserAnAdmin.return_value = True
    admin.ensure_admin()
    shell.ShellExecuteW.assert_not_called()


def test_source_relaunch_preserves_interpreter_arguments_and_directory(shell, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "executable", r"C:\My Project\.venv\Scripts\python.exe")
    monkeypatch.setattr(sys, "argv", ["Main.py", "argument with spaces", 'quoted"value'])
    with pytest.raises(SystemExit) as result:
        admin.ensure_admin()
    assert result.value.code == 0
    shell.ShellExecuteW.assert_called_once_with(
        None, "runas", sys.executable,
        subprocess.list2cmdline([str(tmp_path / "Main.py"), *sys.argv[1:]]),
        str(tmp_path), 1,
    )


def test_frozen_launcher_does_not_pass_executable_as_argument(shell, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True)
    monkeypatch.setattr(sys, "argv", ["Launcher.exe", "--example"])
    with pytest.raises(SystemExit):
        admin.ensure_admin()
    assert shell.ShellExecuteW.call_args.args[3] == "--example"


@pytest.mark.parametrize("error", [0, 2, 5, 31, 32])
def test_denied_request_exits_without_running_bot(shell, error):
    shell.ShellExecuteW.return_value = error
    with pytest.raises(SystemExit) as result:
        admin.ensure_admin()
    assert result.value.code == 1
    assert shell.ShellExecuteW.call_count == 1


def test_non_windows_does_not_request_elevation(shell, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    admin.ensure_admin()
    shell.IsUserAnAdmin.assert_not_called()
