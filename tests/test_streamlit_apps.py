#!/usr/bin/env python3
"""
Smoke tests for the two Streamlit apps (basic and advanced).

Each test starts the app headlessly on a dedicated port,
waits for the server to be ready, verifies key page content,
and then shuts the server down cleanly.

Run with:
  python -m unittest tests/test_streamlit_apps.py -v
"""

import os
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = REPO_ROOT / "src" / "apps"


def wait_for_http(url: str, expect_substring: str, timeout: float = 60.0) -> str:
    """Poll a URL until it returns 200 and contains the expected substring.

    Returns the response text on success, raises AssertionError on timeout.
    """
    start = time.time()
    last_err = None
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200 and expect_substring in r.text:
                return r.text
        except Exception as e:
            last_err = e
        time.sleep(0.5)
    raise AssertionError(f"Timed out waiting for {url}. Last error: {last_err}")


def _pick_python_for_streamlit() -> str:
    """Pick a Python executable that has Streamlit available.

    Tries `python`, then `python3`, then the current interpreter.
    """
    candidates = ["python", "python3", sys.executable]
    for cand in candidates:
        try:
            res = subprocess.run(
                [cand, "-m", "streamlit", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if res.returncode == 0 and "Streamlit" in (res.stdout + res.stderr):
                return cand
        except Exception:
            continue
    # Fallback — will likely fail later, but keeps behavior predictable
    return sys.executable


def run_streamlit(app_path: Path, port: int) -> subprocess.Popen:
    """Start a Streamlit app headlessly on the given port.

    Returns the Popen process handle.
    """
    env = os.environ.copy()
    # Keep Streamlit quiet and headless for CI
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    # Ensure we run from repo root for relative paths used by apps
    cwd = str(REPO_ROOT)

    # Use the default `python` interpreter which (in this repo) has Streamlit installed.
    python_cmd = _pick_python_for_streamlit()
    cmd = [
        python_cmd,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--server.address",
        "127.0.0.1",
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]

    # Start the app; capture stdout/stderr for debugging if needed
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc


def stop_process(proc: subprocess.Popen) -> None:
    """Terminate a process gracefully, then force-kill if needed."""
    if proc.poll() is not None:
        return
    try:
        # SIGINT to allow Streamlit to clean up
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=10)
            return
        except subprocess.TimeoutExpired:
            pass
        proc.terminate()
        try:
            proc.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            pass
        proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


class TestStreamlitApps(unittest.TestCase):
    maxDiff = None

    def test_basic_app_starts(self):
        app = APPS_DIR / "app.py"
        self.assertTrue(app.exists(), f"Missing app: {app}")
        proc = run_streamlit(app, port=8501)
        try:
            html = wait_for_http(
                "http://127.0.0.1:8501",
                "Frequenz SDK — AI‑Native Knowledge Graph",
                timeout=90.0,
            )
            self.assertIn("Frequenz SDK", html)
        finally:
            stop_process(proc)

    def test_advanced_app_starts(self):
        app = APPS_DIR / "app_advanced.py"
        self.assertTrue(app.exists(), f"Missing app: {app}")
        proc = run_streamlit(app, port=8503)
        try:
            html = wait_for_http(
                "http://127.0.0.1:8503",
                "Frequenz SDK — AI Assistant",
                timeout=90.0,
            )
            # Page should show assistant header even without API keys
            self.assertIn("Frequenz SDK", html)
        finally:
            stop_process(proc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
