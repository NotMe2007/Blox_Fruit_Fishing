import os
import sys
import json
import shutil
import zipfile
import subprocess
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

REPO_OWNER = "NotMe2007"
REPO_NAME = "Blox_Fruit_Fishing"
VERSION_FILE = Path("version.txt")
UPDATES_DIR = Path("updates")
HEADERS = {"User-Agent": "BloxFruitLauncher"}
MIN_PYTHON = (3, 8)
DEFAULT_REQUIREMENTS = [
    "customtkinter>=5.2.2",
    "pillow>=11.1.0",
    "numpy",
    "opencv-python",
    "psutil",
    "pywin32",
    "requests",
]


def print_header() -> None:
    print("\n========================================")
    print("  BLOX FRUIT FISHING - AUTO LAUNCHER")
    print("========================================\n")


def ensure_working_directory() -> None:
    os.chdir(Path(__file__).resolve().parent)


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
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(extract_to)
        # GitHub archives expand into a folder named repo-tag
        inner_dirs = [p for p in extract_to.iterdir() if p.is_dir()]
        return inner_dirs[0] if inner_dirs else None
    except (zipfile.BadZipFile, OSError, IndexError):
        return None


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

    if local_version == latest_version:
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


def ensure_python_version() -> None:
    version_info = sys.version_info
    detected = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
    print("[STEP 1] Checking Python installation...")
    print(f" ✅ Python is installed\nPython {detected}")

    if version_info < MIN_PYTHON:
        required = ".".join(map(str, MIN_PYTHON))
        print(f" ❌ Python version is too old (need {required}+). Detected: {detected}")
        sys.exit(1)
    print("\n[STEP 1.5] Checking Python version...")
    print(" ✅ Python version is compatible\n")


def resolve_python_commands() -> tuple[list[str], list[str]]:
    venv_python = Path(".venv") / "Scripts" / "python.exe"
    if venv_python.exists():
        python_cmd = [str(venv_python)]
        pip_cmd = python_cmd + ["-m", "pip"]
        print("[STEP 2] Checking virtual environment...")
        print(" ✅ Virtual environment found\n")
    else:
        python_cmd = [sys.executable]
        pip_cmd = python_cmd + ["-m", "pip"]
        print("[STEP 2] Checking virtual environment...")
        print(" ⚠️  No virtual environment found. Using system Python and pip.\n")
    return python_cmd, pip_cmd


def ensure_requirements(pip_cmd: list[str]) -> None:
    print("[STEP 3] Checking requirements...")
    requirements_path = Path("requirements.txt")
    if not requirements_path.exists():
        print(" ❌ requirements.txt not found! Creating a default one...")
        requirements_path.write_text("\n".join(DEFAULT_REQUIREMENTS) + "\n", encoding="utf-8")
        print(" ✅ Created basic requirements.txt")

    print(" Installing/updating dependencies...")
    result = subprocess.run(pip_cmd + ["install", "-r", "requirements.txt", "--upgrade"], check=False)
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
    result = subprocess.run(python_cmd + [str(quick_test)], check=False)
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
    print_header()
    ensure_working_directory()
    check_for_updates()
    ensure_python_version()
    python_cmd, pip_cmd = resolve_python_commands()
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
