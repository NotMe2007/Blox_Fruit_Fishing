"""Request Windows elevation once, before application startup."""
import ctypes
import os
from pathlib import Path
import subprocess
import sys


def ensure_admin():
    """Continue if elevated; otherwise relaunch through the normal UAC prompt.

    The original process exits after the request, including when it is denied.
    Importing this module never triggers UAC.
    """
    if sys.platform != "win32":
        return
    shell32 = ctypes.windll.shell32
    if shell32.IsUserAnAdmin():
        return

    if getattr(sys, "frozen", False):
        arguments = sys.argv[1:]
    else:
        arguments = [str(Path(sys.argv[0]).resolve()), *sys.argv[1:]]

    shell32.ShellExecuteW.argtypes = [
        ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p,
        ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_int,
    ]
    shell32.ShellExecuteW.restype = ctypes.c_ssize_t
    print("Requesting administrator access. Please accept the Windows UAC prompt.")
    result = shell32.ShellExecuteW(
        None, "runas", sys.executable, subprocess.list2cmdline(arguments),
        os.getcwd(), 1,
    )
    if result <= 32:
        print("Administrator access was cancelled or could not be granted. The bot was not started.")
        raise SystemExit(1)
    raise SystemExit(0)
