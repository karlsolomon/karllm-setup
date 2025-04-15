#!/usr/bin/env python3

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REQUIRED_COMMANDS = ["git", "python3", "uv", "openssl"]
PYTHON_VERSION = "3.12.9"
REPO_URL = "https://github.com/karlsolomon/karllm-client.git"


def assert_env_vars():
    for var in ["XDG_CONFIG_HOME", "HOME"]:
        if var not in os.environ:
            sys.exit(f"Error: ${var} environment variable is not set.")
    print("✔ Environment variables set.")


def assert_commands_exist():
    missing = []
    for cmd in REQUIRED_COMMANDS:
        if shutil.which(cmd) is None:
            missing.append(cmd)
    if missing:
        sys.exit(f"Error: Missing required tools: {', '.join(missing)}")
    print("✔ Required commands installed.")


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


def get_username():
    while True:
        uname = input("Enter a username (alphanumeric only, no spaces): ").strip()
        if re.fullmatch(r"[A-Za-z0-9_]+", uname):
            print(f"✔ Username accepted: {uname}")
            return uname
        print("✘ Invalid username. Try again.")


def ensure_config_dir():
    config_dir = Path(os.environ["XDG_CONFIG_HOME"]) / "karllm"
    config_dir.mkdir(parents=True, exist_ok=True)
    print(f"✔ Config directory ensured at {config_dir}")
    return config_dir


def write_config_file(config_path, uname, priv_key_path):
    if config_path.exists():
        print(f"✔ Config file already exists at {config_path}")
        return
    config_data = {
        "username": uname,
        "secret": str(priv_key_path),
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
    pip_cmd = [
        str(project_path / ".venv" / "bin" / "uv"),
        "pip",
        "install",
        "-r",
        "requirements.txt",
    ]
    subprocess.run(pip_cmd, cwd=project_path, check=True)
    print("✔ Dependencies installed from requirements.txt")


def main():
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
    main()
