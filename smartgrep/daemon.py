import os
import signal
import subprocess
import time
from pathlib import Path

DAEMON_PID_FILE = Path(".smartgrep/daemon.pid")
DAEMON_LOG_FILE = Path(".smartgrep/daemon.log")
HOST = "127.0.0.1"
PORT = 8000

def get_pid():
    if not DAEMON_PID_FILE.exists():
        return None
    try:
        pid = int(DAEMON_PID_FILE.read_text())
        # Check if process is running
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError):
        DAEMON_PID_FILE.unlink()
        return None

def start_daemon():
    if get_pid():
        print("Daemon is already running.")
        return

    DAEMON_PID_FILE.parent.mkdir(exist_ok=True)

    # Start the server as a detached process
    proc = subprocess.Popen(
        ["uvicorn", "smartgrep.server:app", f"--host={HOST}", f"--port={PORT}"],
        stdout=open(DAEMON_LOG_FILE, "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    DAEMON_PID_FILE.write_text(str(proc.pid))
    print(f"Daemon started with PID {proc.pid}. See logs at {DAEMON_LOG_FILE}")

    # Wait a moment for the server to start
    time.sleep(3)

def stop_daemon():
    pid = get_pid()
    if not pid:
        print("Daemon is not running.")
        return

    try:
        os.kill(pid, signal.SIGTERM)
        DAEMON_PID_FILE.unlink()
        print(f"Daemon with PID {pid} stopped.")
    except ProcessLookupError:
        print(f"Daemon with PID {pid} not found. Removing stale PID file.")
        DAEMON_PID_FILE.unlink()

def get_daemon_status():
    if get_pid():
        return "running"
    return "stopped"
