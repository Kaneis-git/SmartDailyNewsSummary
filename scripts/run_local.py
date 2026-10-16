"""Install local dependencies and supervise API, worker and Vite. No Docker.

Windows: double-click start-windows.cmd. Python 3.12 and Node 24.15+ are
required. This launcher uses only the Python standard library.
The API automatically uses a free loopback port from 8000 through 8099.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
RUNTIME = ROOT / "output" / "local-run"
URL = "http://localhost:3000"
# Local health checks must not go through an HTTP proxy configured for news.
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def say(message):
    print(message, flush=True)


@contextmanager
def single_instance():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with (RUNTIME / "launcher.lock").open("a+b") as lock:
        lock.seek(0, 2)
        if lock.tell() == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("This project's launcher is already running. Use its window.") from exc
        yield


def require_tools():
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Run this launcher with Python 3.12 (py -3.12 on Windows).")
    node = shutil.which("node")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not node or not npm:
        raise RuntimeError("Install Node.js 24 LTS (24.15 or newer), reopen the launcher, and try again. https://nodejs.org/en/download")
    version = subprocess.check_output([node, "--version"], text=True).strip()
    parts = tuple(int(p) for p in version.lstrip("v").split("."))
    if parts[0] != 24 or parts < (24, 15, 0):
        raise RuntimeError(f"Found Node {version}. This launcher uses Node 24 LTS, version 24.15 or newer within 24.x.")
    npm_command = [npm]
    if os.name == "nt":
        # Run npm's JavaScript entry with node, without cmd/PowerShell parsing.
        candidates = [Path(npm).parent / "node_modules/npm/bin/npm-cli.js",
                      Path(node).parent / "node_modules/npm/bin/npm-cli.js"]
        cli = next((p for p in candidates if p.is_file()), None)
        if cli is None:
            raise RuntimeError("npm-cli.js was not found. Reinstall the official Node.js Windows installer with npm enabled.")
        npm_command = [node, str(cli)]
    say(f"Python {sys.version.split()[0]} | Node {version}")
    return node, npm_command, version


def require_free_ports(ports=(3000,)):
    for port in ports:
        with socket.socket() as sock:
            if os.name != "nt":
                # A stopped HTTP server may leave TIME_WAIT sockets behind.
                # Windows SO_REUSEADDR has different semantics; do not use it there.
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError as exc:
                raise RuntimeError(f"Port {port} is unavailable. Check the existing application or Windows reservation. No process was stopped.") from exc


def choose_api_port(first=8000, last=8099):
    """Skip occupied or OS-reserved ports without stopping their owners."""
    for port in range(first, last + 1):
        try:
            require_free_ports((port,))
        except RuntimeError:
            continue
        return port
    raise RuntimeError(f"No available API port between {first} and {last}. No process was stopped.")


def fingerprint(paths, extra=""):
    value = hashlib.sha256(extra.encode())
    for path in paths:
        value.update(path.read_bytes())
    return value.hexdigest()


def matches(path, expected):
    return path.is_file() and path.read_text(encoding="utf-8").strip() == expected


def prepare_dependencies(npm_command, node_version, repair):
    environment = ROOT / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        if environment.exists():
            raise RuntimeError("An incomplete .venv exists. Rename it to .venv-backup and retry; it was not removed.")
        say("[1/4] Creating the Python environment...")
        subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
    check = subprocess.run([str(python), "-c", "import sys; sys.exit(sys.version_info[:2] != (3,12))"])
    if check.returncode:
        raise RuntimeError(".venv needs Python 3.12. Rename it to .venv-backup and retry.")
    requirements = ROOT / "backend" / "requirements.txt"
    expected = fingerprint([requirements])
    marker = environment / ".news-dependencies"
    if repair or not matches(marker, expected):
        say("[1/4] Installing Python dependencies (first run requires Internet)...")
        subprocess.run([str(python), "-m", "pip", "install", "-r", str(requirements)], check=True, cwd=ROOT)
        marker.write_text(expected, encoding="utf-8")
    else:
        say("[1/4] Python dependencies ready.")
    expected = fingerprint([FRONTEND / "package.json", FRONTEND / "package-lock.json"], node_version)
    marker = FRONTEND / "node_modules" / ".news-dependencies"
    vite = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"
    if repair or not vite.is_file() or not matches(marker, expected):
        say("[2/4] Installing web dependencies (first run requires Internet)...")
        subprocess.run([*npm_command, "ci", "--include=dev"], check=True, cwd=FRONTEND)
        marker.write_text(expected, encoding="utf-8")
    else:
        say("[2/4] Web dependencies ready.")
    if not (ROOT / ".env").exists():
        shutil.copyfile(ROOT / ".env.example", ROOT / ".env")
        say("Created .env from the template. AI is optional; configure it later.")
    return python, vite


def start(name, command, directory, services, environment=None):
    log_path = RUNTIME / f"{name}.log"
    with log_path.open("w", encoding="utf-8") as log:
        kwargs = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
        process = subprocess.Popen(command, cwd=directory, stdout=log, stderr=subprocess.STDOUT,
                                   env={**os.environ, **(environment or {}), "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}, **kwargs)
    services.append((name, process, log_path))


def check_services(services):
    for name, process, log in services:
        code = process.poll()
        if code is not None:
            raise RuntimeError(f"{name} stopped (exit {code}). Details: {log}")


def wait_ready(url, services, worker=False):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        check_services(services)
        try:
            with HTTP.open(url, timeout=2) as response:
                if response.status == 200 and (not worker or json.load(response).get("worker_online")):
                    return
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            pass
        time.sleep(0.4)
    raise RuntimeError(f"Startup timed out: {url}. See logs in {RUNTIME}")


def stop_services(services):
    if not services:
        return
    say("Stopping project services...")
    for _, process, _ in reversed(services):
        if process.poll() is not None:
            continue
        try:
            if os.name == "nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                os.killpg(process.pid, signal.SIGINT)
            process.wait(timeout=6)
        except (OSError, subprocess.TimeoutExpired):
            if process.poll() is None:
                if os.name != "nt":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    # Only this launcher's child PID and descendants are stopped.
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
                process.wait(timeout=5)
    say("Stopped. Database and configuration have been kept.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--repair", action="store_true", help="Reinstall pinned dependencies without deleting database/configuration")
    args = parser.parse_args()
    services = []
    try:
        with single_instance():
            try:
                node, npm, version = require_tools()
                require_free_ports()
                python, vite = prepare_dependencies(npm, version, args.repair)
                require_free_ports()
                api_port = choose_api_port()
                api_url = f"http://127.0.0.1:{api_port}"
                health_url = f"{api_url}/api/v1/health"
                say(f"API address: {api_url}")
                if api_port != 8000:
                    say(f"Port 8000 is unavailable; using {api_port}. Web requests will use this port automatically.")
                say("[3/4] Starting API and scheduled worker...")
                start("api", [str(python), "manage.py", "api", "--port", str(api_port)], ROOT, services)
                wait_ready(health_url, services)
                start("worker", [str(python), "manage.py", "worker"], ROOT, services)
                wait_ready(health_url, services, worker=True)
                say("[4/4] Starting the web application...")
                start("web", [node, str(vite), "--host", "127.0.0.1", "--port", "3000", "--strictPort"], FRONTEND, services,
                      environment={"AI_NEWS_API_TARGET": api_url})
                wait_ready("http://127.0.0.1:3000", services)
                # Confirm that browser requests can reach the API through Vite.
                wait_ready("http://127.0.0.1:3000/api/v1/health", services, worker=True)
                say(f"READY: {URL}\nKeep this window open. Press Ctrl+C here to stop.\nLogs: {RUNTIME}")
                if not args.no_browser:
                    try:
                        webbrowser.open(URL)
                    except webbrowser.Error:
                        say(f"Open {URL} in your browser.")
                while True:
                    check_services(services)
                    time.sleep(1)
            finally:
                stop_services(services)
    except KeyboardInterrupt:
        say("Cancelled.")
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        say(f"ERROR: {exc}\nSee docs/WINDOWS_LOCAL_START.md. Send the error or the relevant log if you need help.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
