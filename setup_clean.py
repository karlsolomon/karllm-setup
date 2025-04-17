#!/usr/bin/env python3

import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


def bootstrap_dependencies():
    import importlib.util

    def is_module_installed(name):
        return importlib.util.find_spec(name) is not None

    # # Ensure PyYAML
    # if not is_module_installed("yaml"):
    #     print("⏳ Installing required module: PyYAML...")
    #     subprocess.check_call([sys.executable, "-m", "pip", "install", "PyYAML"])
    #
    # Ensure uv CLI exists
    if shutil.which("uv") is None:
        print("⏳ Installing required CLI tool: uv...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "uv"])

    print("✔ Script-level dependencies verified.")


IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"


def normalize_env():
    if IS_WINDOWS:
        print(
            "⚠ Windows detected. For best results, run this script from Git Bash or WSL."
        )
        # Set fallback HOME for Git Bash or PowerShell
        if "HOME" not in os.environ:
            os.environ["HOME"] = str(Path.home())

        # Fallback XDG_CONFIG_HOME
        if "XDG_CONFIG_HOME" not in os.environ:
            os.environ["XDG_CONFIG_HOME"] = str(
                Path(os.environ["HOME"]) / "AppData" / "Roaming"
            )

    elif IS_MAC or IS_LINUX:
        if "XDG_CONFIG_HOME" not in os.environ:
            os.environ["XDG_CONFIG_HOME"] = str(Path(os.environ["HOME"]) / ".config")

    else:
        sys.exit(
            "❌ Unsupported platform. This script only supports Linux, macOS, and Windows."
        )


normalize_env()


REQUIRED_COMMANDS = ["git", "python3", "uv", "openssl"]
PYTHON_VERSION = "3.12.9"
REPO_URL = "https://github.com/karlsolomon/karllm-client.git"


def assert_env_vars():
    for var in ["XDG_CONFIG_HOME", "HOME"]:
        if var not in os.environ:
            sys.exit(f"Error: ${var} environment variable is not set.")
    print("✔ Environment variables set.")


def get_linux_package_manager():
    try:
        with open("/etc/os-release") as f:
            os_release = f.read().lower()

        if "arch" in os_release:
            return "pacman"
        elif "debian" in os_release or "ubuntu" in os_release:
            return "apt"
        elif "fedora" in os_release or "rhel" in os_release:
            return "dnf"
        elif "alpine" in os_release:
            return "apk"
        else:
            return "unknown"
    except FileNotFoundError:
        if (
            platform.platform().contains("android") and platform.machine() == "aarch64"
        ):  # Handle TERMUX
            return "pkg"
        else:
            return "unknown"
    except Exception:
        return "unknown"


def assert_commands_exist():
    missing = []
    for cmd in REQUIRED_COMMANDS:
        if shutil.which(cmd) is None:
            missing.append(cmd)

    if not missing:
        print("✔ Required system tools are installed.")
        return

    print("\n❌ The following required system tools are missing:")
    for cmd in missing:
        print(f"   - {cmd}")

    print("\n🔧 To install them:")

    if IS_LINUX:
        pkg = get_linux_package_manager()
        print(f"🟢 Linux detected ({pkg})")

        if pkg == "pacman":
            install_cmds = {
                "git": "sudo pacman -S git",
                "rust": "sudo pacman -S rust",
                "openssl": "sudo pacman -S openssl",
                "python3": "sudo pacman -S python",
            }
        elif pkg == "apt":
            install_cmds = {
                "git": "sudo apt install git",
                "rust": "sudo apt install rust",
                "openssl": "sudo apt install openssl",
                "python3": "sudo apt install python3",
            }
        elif pkg == "dnf":
            install_cmds = {
                "git": "sudo dnf install git",
                "rust": "sudo dnf install rust",
                "openssl": "sudo dnf install openssl",
                "python3": "sudo dnf install python3",
            }
        elif pkg == "apk":
            install_cmds = {
                "git": "apk add git",
                "rust": "apk add rust",
                "openssl": "apk add openssl",
                "python3": "apk add python3",
            }
        elif pkg == "pkg":
            install_cmds = {
                "git": "pkg install git",
                "rust": "pkg install rust",
                "openssl": "pkg install openssl",
                "openssh": "pkg install openssh",
                "python3": "pkg install python3",
            }
        else:
            print("⚠ Unsupported or unknown Linux distro.")
            install_cmds = {}
    elif IS_MAC:
        print("🍎 macOS detected. If you have Homebrew:")
        install_cmds = {
            "git": "brew install git",
            "openssl": "brew install openssl",
            "python3": "brew install python@3.12",
        }
    elif IS_WINDOWS:
        print("🪟 Windows detected. Try one of the following:")
        install_cmds = {
            "git": "winget install --id Git.Git -e",
            "openssl": "winget install --id ShiningLight.OpenSSL -e",
            "python3": "winget install --id Python.Python.3.12 -e",
        }
        print("🟡 Or use Chocolatey: https://chocolatey.org/install")
    else:
        print("⚠ Unknown platform — please install manually.")
        install_cmds = {}

    for cmd in missing:
        if cmd == "uv":
            print(f"   - uv: pip install --user uv  # or pipx install uv")
        elif cmd in install_cmds:
            print(f"   - {cmd}: {install_cmds[cmd]}")
        else:
            print(f"   - {cmd}: install manually")

    sys.exit("\n💥 Aborting setup due to missing tools.\n")


def ensure_python_version():
    print(f"🔍 Checking if Python {PYTHON_VERSION} is available...")
    result = subprocess.run(
        ["uv", "python", "find", f"{PYTHON_VERSION}"], capture_output=True, text=True
    )
    if PYTHON_VERSION not in result.stdout:
        print(f"⏬ Python {PYTHON_VERSION} not found. Installing...")
        subprocess.run(["uv", "python", "install", PYTHON_VERSION], check=True)
        print(f"✔ Installed Python {PYTHON_VERSION}")
    else:
        print(f"✔ Python {PYTHON_VERSION} already available.")


def ensure_config_dir():
    config_dir = Path(os.environ["XDG_CONFIG_HOME"]) / "karllm"
    config_dir.mkdir(parents=True, exist_ok=True)
    print(f"✔ Config directory ensured at {config_dir}")
    return config_dir


def write_config_file(config_path, uname, priv_key_path):
    import yaml

    if config_path.exists():
        print(f"✔ Config file already exists at {config_path}")
        return
    config_data = {
        "username": uname,
        "secret": str(priv_key_path),
        "saveInteraction": True,
    }
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)
    print(f"✔ Config written to {config_path}")


def generate_keypair(config_dir, uname):
    priv_path = config_dir / f"{uname}.priv"
    pub_path = config_dir / f"{uname}.pub"
    if priv_path.exists() and pub_path.exists():
        print("✔ Keypair already exists.")
        return priv_path, pub_path

    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(priv_path)],
        check=True,
    )
    subprocess.run(
        ["openssl", "pkey", "-in", str(priv_path), "-pubout", "-out", str(pub_path)],
        check=True,
    )
    print(f"✔ ED25519 keypair generated: {priv_path}, {pub_path}")
    return priv_path, pub_path


def clone_repo(home_path):
    target_path = home_path / "karllm-client"
    if target_path.exists():
        print("✔ Repo already cloned.")
        return target_path
    subprocess.run(["git", "clone", REPO_URL, str(target_path)], check=True)
    print(f"✔ Repo cloned to {target_path}")
    return target_path


def setup_venv(project_path):
    subprocess.run(
        ["uv", "venv", "--python", PYTHON_VERSION, ".venv"],
        cwd=str(project_path),
        check=True,
    )
    print(f"✔ Virtual environment created with Python {PYTHON_VERSION}")


def install_requirements(project_path):
    uv_path = (
        project_path / ".venv" / "Scripts" / "uv"
        if IS_WINDOWS
        else project_path / ".venv" / "bin" / "uv"
    )
    if not uv_path.exists():
        sys.exit("❌ uv not found inside venv. Ensure uv venv worked correctly.")

    subprocess.run(
        [str(uv_path), "pip", "install", "-r", "requirements.txt"],
        cwd=project_path,
        check=True,
    )
    print("✔ Requirements installed using uv inside virtual environment")


def get_username():
    if "--username" in sys.argv:
        idx = sys.argv.index("--username")
        if idx + 1 < len(sys.argv):
            uname = sys.argv[idx + 1].strip()
            if re.fullmatch(r"[A-Za-z0-9_]+", uname):
                print(f"✔ Username accepted (CLI): {uname}")
                return uname
            else:
                sys.exit("✘ Invalid username provided via CLI.")
    # fallback to interactive
    while True:
        uname = input("Enter a username (alphanumeric only, no spaces): ").strip()
        if re.fullmatch(r"[A-Za-z0-9_]+", uname):
            print(f"✔ Username accepted: {uname}")
            return uname
        print("✘ Invalid username. Try again.")


def main():
    bootstrap_dependencies()
    assert_env_vars()
    assert_commands_exist()
    ensure_python_version()

    uname = get_username()
    config_dir = ensure_config_dir()
    priv_key_path, _ = generate_keypair(config_dir, uname)
    write_config_file(config_dir / "karllm.conf", uname, priv_key_path)

    home = Path(os.environ["HOME"])
    project_path = clone_repo(home)
    setup_venv(project_path)
    install_requirements(project_path)

    print("✅ Setup complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⛔ Setup interrupted by user.")
