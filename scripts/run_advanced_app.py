#!/usr/bin/env python3
"""
Run the advanced Streamlit app with sane defaults, logs, and PID control.
Uses .streamlit/config.toml for branding and stores runtime files in temp/.

Usage:
  python scripts/run_advanced_app.py              # start on port 8503
  python scripts/run_advanced_app.py -p 8600      # start on custom port
  python scripts/run_advanced_app.py -k           # kill existing process and exit
"""

import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path


def setup_directories():
    """Ensure temp directories exist and return run + streamlit dirs."""
    temp_dir = Path("temp")
    run_dir = temp_dir / ".run"
    streamlit_dir = Path(".streamlit")

    temp_dir.mkdir(exist_ok=True)
    run_dir.mkdir(exist_ok=True)
    streamlit_dir.mkdir(exist_ok=True)

    return run_dir, streamlit_dir


def kill_existing_process(pid_file: Path):
    """Kill an existing process recorded in pid_file, if any."""
    if not pid_file.exists():
        return
    try:
        pid = int(pid_file.read_text().strip())
    except Exception:
        pid_file.unlink(missing_ok=True)
        return

    try:
        if os.name == "nt":  # Windows
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)], capture_output=True, check=False
            )
        else:  # Unix-like
            os.kill(pid, signal.SIGTERM)
        print(f"✅ Stopped existing process (PID: {pid})")
    except Exception:
        pass
    finally:
        pid_file.unlink(missing_ok=True)


def run_streamlit_app(port: int, run_dir: Path, streamlit_dir: Path) -> bool:
    """Start Streamlit for the enhanced app headlessly on the given port."""
    app_file = "src/apps/app_advanced.py"
    pid_file = run_dir / f"streamlit_advanced.{port}.pid"
    log_file = run_dir / f"streamlit_advanced.{port}.log"

    # Stop any previous instance
    kill_existing_process(pid_file)

    # Environment for Streamlit
    env = os.environ.copy()
    env["STREAMLIT_CONFIG_DIR"] = str(streamlit_dir)
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        app_file,
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--global.developmentMode",
        "false",
    ]

    print(f"🚀 Starting advanced app on port {port}…")
    print(f"📝 Logs: {log_file}")
    try:
        with open(log_file, "w") as log:
            proc = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=str(Path.cwd()),
                text=True,
            )
        pid_file.write_text(str(proc.pid))
        print("✅ Advanced app started!")
        print(f"🌐 Open: http://127.0.0.1:{port}")
        print(f"🆔 PID: {proc.pid}")
        print(f"📁 Runtime: {run_dir}")
        return True
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run AI‑enhanced Streamlit app with logging and PID control"
    )
    parser.add_argument(
        "--port", "-p", type=int, default=8503, help="Port to run on (default: 8503)"
    )
    parser.add_argument(
        "--kill", "-k", action="store_true", help="Kill existing process and exit"
    )
    args = parser.parse_args()

    run_dir, streamlit_dir = setup_directories()

    if args.kill:
        kill_existing_process(run_dir / f"streamlit_advanced.{args.port}.pid")
        print("🛑 Process killed (if it was running)")
        return

    success = run_streamlit_app(args.port, run_dir, streamlit_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
