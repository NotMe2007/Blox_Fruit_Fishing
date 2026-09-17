import sys

# Redirected Windows output may use an encoding without emoji support.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(errors="replace")

import os
import re
import shlex
import sys
import json
import shutil
import zipfile
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

REPO_OWNER = "NotMe2007"
REPO_NAME = "Blox_Fruit_Fishing"
VERSION_FILE = Path("version.txt")
UPDATES_DIR = Path("updates")
HEADERS = {"User-Agent": "BloxFruitLauncher"}
MIN_PYTHON = (3, 10)
DEFAULT_REQUIREMENTS = [
    "customtkinter>=5.2.2",
    "pillow>=11.1.0",
    "numpy",
    "opencv-python",
    "psutil",
    "pywin32; platform_system == 'Windows'",
    "keyboard",
    "requests",
]


def _get_python_version(python_cmd: list[str]) -> tuple[str, tuple[int, int, int]]:
    try:
        result = subprocess.run(
            python_cmd + ["--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError) as exc:
        raise RuntimeError(f"Unable to execute {' '.join(python_cmd)}: {exc}") from exc

    if result.returncode != 0:
        raise RuntimeError(
            f"Command {' '.join(python_cmd)} --version returned exit code {result.returncode}"
        )

    version_output = (result.stdout or result.stderr or "").strip()
    match = re.search(r"Python\s+(\d+)\.(\d+)\.(\d+)", version_output)
    if not match:
        raise RuntimeError(f"Could not parse Python version from '{version_output}'.")

    major, minor, patch = (int(part) for part in match.groups())
    version_tuple = (major, minor, patch)
    return version_output, version_tuple


def _venv_python_path() -> Path:
    if os.name == "nt":
        return Path(".venv") / "Scripts" / "python.exe"
    return Path(".venv") / "bin" / "python"


def acquire_python_command() -> tuple[list[str], bool, str, tuple[int, int, int]]:
    candidates: list[tuple[list[str], bool]] = []
    venv_python = _venv_python_path()

    if venv_python.exists():
        candidates.append(([str(venv_python)], True))

    override_cmd = os.environ.get("BFF_PYTHON_CMD")
    if override_cmd:
        candidates.append((shlex.split(override_cmd), False))

    if not getattr(sys, "frozen", False):
        candidates.append(([sys.executable], False))

    names = ["python3", "python"] if os.name != "nt" else [
        "python.exe",
        "python3.exe",
        "python",
    ]
    for name in names:
        path = shutil.which(name)
        if path:
            candidates.append(([path], False))

    if os.name == "nt" and shutil.which("py"):
        candidates.append((["py", "-3"], False))

    seen: set[tuple[str, ...]] = set()
    for command, is_venv in candidates:
        key = tuple(command)
        if key in seen:
            continue
        seen.add(key)
        try:
            version_text, version_tuple = _get_python_version(command)
            return command, is_venv, version_text, version_tuple
        except RuntimeError:
            continue

    raise RuntimeError(
        "Unable to locate a working Python interpreter. Install Python 3.10+ or create a "
        "virtual environment in this folder."
    )


def print_header() -> None:
    print("\n========================================")
    print("  BLOX FRUIT FISHING - AUTO LAUNCHER")
    print("========================================\n")


def ensure_working_directory() -> None:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
        if not (base_dir / "Main.py").exists() and (base_dir.parent / "Main.py").exists():
            base_dir = base_dir.parent
    else:
        base_dir = Path(__file__).resolve().parent
    os.chdir(base_dir)


def read_local_version() -> str:
    if VERSION_FILE.exists():
        try:
            value = VERSION_FILE.read_text(encoding="utf-8").strip()
            return value or "unknown"
        except OSError:
            return "unknown"
    return "unknown"


def fetch_json(url: str) -> Optional[dict]:
    request = Request(url, headers=HEADERS)
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def get_latest_release() -> Optional[dict]:
    latest = fetch_json(f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest")
    if latest:
        return latest
    releases = fetch_json(
        f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases?per_page=1"
    )
    if isinstance(releases, list) and releases:
        return releases[0]
    return None


def download_release(tag: str, destination: Path) -> bool:
    url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/tags/{tag}.zip"
    request = Request(url, headers=HEADERS)
    try:
        with urlopen(request, timeout=60) as response:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with open(destination, "wb") as handle:
                shutil.copyfileobj(response, handle)
        return True
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def extract_archive(archive: Path, extract_to: Path) -> Optional[Path]:
    try:
        extract_to.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix="release-", dir=extract_to))
        with zipfile.ZipFile(archive, "r") as zf:
            for member in zf.infolist():
                target = (staging / member.filename).resolve()
                if not target.is_relative_to(staging.resolve()):
                    raise ValueError("Archive path escapes the release directory")
            zf.extractall(staging)
        # GitHub archives expand into a folder named repo-tag
        inner_dirs = [p for p in staging.iterdir() if p.is_dir()]
        if len(inner_dirs) != 1 or not (inner_dirs[0] / "Main.py").is_file():
            return None
        return inner_dirs[0]
    except (zipfile.BadZipFile, OSError, ValueError):
        return None


def version_key(value: str):
    """Compare numeric releases independently of V/v prefixes."""
    match = re.fullmatch(r"[vV]?(\d+)\.(\d+)\.(\d+)", value.strip())
    return tuple(map(int, match.groups())) if match else None


def copy_tree(src: Path, dst: Path, exclude: Optional[set] = None) -> None:
    exclude = exclude or set()
    for item in src.iterdir():
        if item.name in exclude:
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def check_for_updates() -> None:
    print("[STEP 0] Checking for updates...")
    if Path(".git").exists():
        print("   Source checkout: update with Git to preserve local changes.")
        return
    local_version = read_local_version()
    release = get_latest_release()
    if not release:
        print(" ⚠️  Could not reach GitHub releases. Continuing without update.")
        return

    latest_version = release.get("tag_name", "unknown") or "unknown"
    is_prerelease = bool(release.get("prerelease"))

    print(f"   Local version: {local_version}")
    print(f"   Latest release: {latest_version}")
    if is_prerelease:
        print("   Release type: pre-release")

    local_key, latest_key = version_key(local_version), version_key(latest_version)
    if latest_key is None:
        print("   Release tag is not a stable version; skipping automatic update.")
        return
    if local_key is not None and local_key >= latest_key:
        print(f" ✅ You already have the latest version ({local_version}).")
        return

    print(
        f" ⚠️  Update available! Local version: {local_version}  Latest version: {latest_version}"
    )
    if is_prerelease:
        print(" 📎 Note: This release is marked as a pre-release on GitHub.")

    UPDATES_DIR.mkdir(exist_ok=True)
    archive_path = UPDATES_DIR / f"{REPO_NAME}_{latest_version}.zip"

    print(" Downloading latest release package...")
    if not download_release(latest_version, archive_path):
        print(" ❌ Failed to download the latest release. Continuing without updating.")
        archive_path.unlink(missing_ok=True)
        return

    print(" ✅ Download complete. Extracting package...")
    extracted_folder = extract_archive(archive_path, UPDATES_DIR)
    if not extracted_folder:
        print(" ❌ Failed to extract update package. Continuing without updating.")
        archive_path.unlink(missing_ok=True)
        return

    # The archive may carry an outdated version file, including in test copies.
    (extracted_folder / "version.txt").write_text(latest_version, encoding="utf-8")
    print(f"\n 📁 Latest version extracted to: {extracted_folder}")
    decision = input(
        "\nWould you like to test the new version before replacing the current install? (Y/N): "
    ).strip().lower()
    if decision == "y":
        print(" ✅ Keeping current installation. Test the update by running Launcher.py inside:")
        print(f"    {extracted_folder}")
        print(" Once satisfied, rerun this launcher to apply the update.")
        archive_path.unlink(missing_ok=True)
        return

    print(f"\n 🔄 Replacing current installation with version {latest_version}...")
    try:
        copy_tree(extracted_folder, Path.cwd(), exclude={".git", "updates"})
        VERSION_FILE.write_text(latest_version, encoding="utf-8")
        print(" ✅ Update applied successfully.")
    except Exception as exc:  # noqa: BLE001
        print(f" ❌ Failed to apply update: {exc}")
    finally:
        archive_path.unlink(missing_ok=True)
        shutil.rmtree(extracted_folder, ignore_errors=True)

    print(" ℹ️  The launcher will now continue using the updated files.\n")


def ensure_python_version(version_text: str, version_info: tuple[int, int, int]) -> None:
    print("[STEP 1] Checking Python installation...")
    print(" ✅ Python is installed")
    print(version_text)

    print("\n[STEP 1.5] Checking Python version...")
    if version_info < MIN_PYTHON:
        required = ".".join(map(str, MIN_PYTHON))
        print(
            f" ❌ Python version is too old (need {required}+). Detected: {version_text}"
        )
        sys.exit(1)
    print(" ✅ Python version is compatible\n")


def ensure_requirements(pip_cmd: list[str]) -> None:
    print("[STEP 3] Checking requirements...")
    requirements_path = Path("requirements.txt")
    if not requirements_path.exists():
        print(" ❌ requirements.txt not found! Creating a default one...")
        requirements_path.write_text("\n".join(DEFAULT_REQUIREMENTS) + "\n", encoding="utf-8")
        print(" ✅ Created basic requirements.txt")

    print(" Installing/updating dependencies...")
    result = subprocess.run(pip_cmd + ["install", "-r", "requirements.txt"], check=False)
    if result.returncode != 0:
        print(" ❌ Failed to install some dependencies. Attempting core packages individually...")
        core_result = subprocess.run(pip_cmd + ["install", "opencv-python", "numpy", "pillow"], check=False)
        if core_result.returncode != 0:
            print(" ❌ Critical dependency installation failed. Please check your environment.")
            sys.exit(1)
    print(" ✅ All dependencies installed successfully\n")


def run_quick_tests(python_cmd: list[str]) -> bool:
    print("[STEP 4] Running system health check...")
    quick_test = Path("tests") / "quick_test.py"
    if not quick_test.exists():
        print(" ❌ Test file not found: tests/quick_test.py. Skipping tests.\n")
        return True

    print(" Running quick diagnostic tests...")
    result = subprocess.run(python_cmd + ["-X", "utf8", str(quick_test)], check=False)
    if result.returncode == 0:
        print(" ✅ ALL TESTS PASSED - System is ready!\n")
        return True

    print(" ⚠️  Some tests failed. Attempting additional diagnostics...")
    diag = subprocess.run(
        python_cmd
        + ["-c", "import cv2, numpy, PIL; print('CORE_OK')"],
        capture_output=True,
        text=True,
        check=False,
    )
    if "CORE_OK" in diag.stdout:
        print(" ✅ Core components working - Minor issues detected.")
        choice = input("Continue anyway? (Y/N): ").strip().lower()
        return choice == "y"

    print(" ❌ Critical component failure detected. Cannot continue.")
    return False


def launch_main_app(python_cmd: list[str]) -> None:
    print("[STEP 5] Launching Blox Fruit Fishing...\n")
    print(" 🎮 IMPORTANT INSTRUCTIONS:")
    print(" 1. Make sure Roblox is running")
    print(" 2. Join Blox Fruits game")
    print(" 3. Go to a fishing area")
    print(" 4. Use numpad keys to control the bot (defaults: 1=start, 2=stop)")
    print("\n Starting GUI...\n")

    if not Path("Main.py").exists():
        print(" ❌ Main.py not found!")
        return

    result = subprocess.run(python_cmd + ["Main.py"], check=False)
    if result.returncode != 0:
        print(" ❌ Application crashed or failed to start. Check the error messages above.")
    else:
        print("\n Application closed normally.")


def main() -> None:
    from Admin_Launch import ensure_admin
    ensure_admin()
    print_header()
    ensure_working_directory()
    check_for_updates()
    try:
        python_cmd, using_venv, version_text, version_info = acquire_python_command()
    except RuntimeError as exc:
        print("[STEP 1] Checking Python installation...")
        print(f" ❌ {exc}")
        print("    Install Python from https://www.python.org/downloads/ to continue.")
        sys.exit(1)

    ensure_python_version(version_text, version_info)

    print("[STEP 2] Checking virtual environment...")
    if using_venv:
        print(" ✅ Virtual environment found\n")
    else:
        readable_cmd = " ".join(python_cmd)
        print(f" ⚠️  No virtual environment found. Using system Python command: {readable_cmd}\n")

    pip_cmd = python_cmd + ["-m", "pip"]
    ensure_requirements(pip_cmd)
    if run_quick_tests(python_cmd):
        launch_main_app(python_cmd)
    else:
        print("\n Exiting due to failed diagnostics. Please resolve the issues above.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n Operation cancelled by user.")
