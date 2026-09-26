"""Small generated guard for Python subprocesses used by document engines."""
from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path

_ENV_NAMES = frozenset({
    "LANG", "LC_ALL", "LC_CTYPE", "PATH", "PATHEXT", "SYSTEMROOT", "TEMP", "TMP", "TMPDIR", "TZ",
    "PLAYWRIGHT_BROWSERS_PATH",
})

_SITE_CUSTOMIZE = (
    "import socket\n"
    "def _deny(*args, **kwargs):\n"
    "    raise OSError('network access is disabled in document engine processes')\n"
    "socket.socket.connect = _deny\n"
    "socket.socket.connect_ex = _deny\n"
    "socket.create_connection = _deny\n"
    "socket.socket.sendto = _deny\n"
    "if hasattr(socket.socket, 'sendmsg'):\n"
    "    socket.socket.sendmsg = _deny\n"
)


def sandbox_environment(directory: str | Path) -> dict[str, str]:
    """Return a reduced environment and install a generated Python network guard."""
    root = Path(directory)
    (root / "sitecustomize.py").write_text(_SITE_CUSTOMIZE, encoding="utf-8")
    environment = {name: value for name, value in os.environ.items() if name in _ENV_NAMES}
    # Chromium needs a writable home/cache location when launched inside the
    # credential-free document worker. Keep those paths inside the disposable
    # per-job directory rather than inheriting an operator's home.
    environment.update({"PYTHONPATH": str(root), "PYTHONNOUSERSITE": "1",
                        "HOME": str(root), "XDG_CONFIG_HOME": str(root / "config"),
                        "XDG_CACHE_HOME": str(root / "cache")})
    return environment


def isolated_process_options() -> dict[str, object]:
    """Return subprocess options that put document engines in a killable group."""
    if os.name == "posix":
        return {"start_new_session": True}
    if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {}


def terminate_process_group(process: subprocess.Popen[bytes] | subprocess.Popen[str]) -> None:
    """Terminate an engine and its descendants where the host exposes groups."""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
            return
        except ProcessLookupError:
            return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)
        return
    process.kill()


def run_engine_command(command: list[str], *, cwd: str | Path,
                       environment: dict[str, str], timeout_seconds: int) -> int:
    """Run a quiet document engine and kill its whole group if it times out."""
    stderr_path = Path(cwd) / "engine.stderr"
    stderr_file = stderr_path.open("wb")
    process = subprocess.Popen(command, cwd=cwd, env=environment,
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=stderr_file, **isolated_process_options())
    try:
        return process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        terminate_process_group(process)
        process.wait()
        raise
    finally:
        stderr_file.close()
