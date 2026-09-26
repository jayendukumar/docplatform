"""Run untrusted document work in a credential-free, bounded child process."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any


class WorkerExecutionError(RuntimeError):
    pass


def _sandbox_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    """Keep only process-launch and locale inputs for untrusted document work."""
    source = source or os.environ
    allowed = {"PATH", "SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR",
               "LANG", "LC_ALL", "PYTHONIOENCODING", "PYTHONUNBUFFERED",
               "PLAYWRIGHT_BROWSERS_PATH"}
    return {name: value for name, value in source.items() if name in allowed}


def _kill_process(process: subprocess.Popen[str]) -> None:
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
            return
        except ProcessLookupError:
            return
    process.kill()


def _assign_windows_job_limits(process: subprocess.Popen[str], cpu_seconds: int,
                                memory_bytes: int):
    """Attach a child to a Windows Job Object with per-process limits.

    The handle is returned to keep the job alive for the duration of the child.
    This is deliberately isolated behind the platform check so Linux containers
    continue to use the child-side POSIX resource limits.
    """
    if os.name != "nt":
        return None
    # Test doubles and alternate process wrappers may not expose the native
    # Windows handle. The real subprocess.Popen implementation does.
    if not hasattr(process, "_handle"):
        return None
    import ctypes
    from ctypes import wintypes

    class BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimitInformation),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, wintypes.INT,
                                                  wintypes.LPVOID, wintypes.DWORD]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise WorkerExecutionError(f"could not create Windows worker job: {ctypes.get_last_error()}")
    limits = ExtendedLimitInformation()
    limits.BasicLimitInformation.PerProcessUserTimeLimit = cpu_seconds * 10_000_000
    # 0x0002 = JOB_OBJECT_LIMIT_PROCESS_TIME; 0x0100 = PROCESS_MEMORY;
    # 0x2000 = KILL_ON_JOB_CLOSE.
    limits.BasicLimitInformation.LimitFlags = 0x0002 | 0x0100 | 0x2000
    limits.ProcessMemoryLimit = memory_bytes
    if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        error = ctypes.get_last_error()
        kernel32.CloseHandle(job)
        raise WorkerExecutionError(f"could not configure Windows worker limits: {error}")
    process_handle = wintypes.HANDLE(process._handle)
    if not kernel32.AssignProcessToJobObject(job, process_handle):
        error = ctypes.get_last_error()
        kernel32.CloseHandle(job)
        raise WorkerExecutionError(f"could not assign Windows worker limits: {error}")
    return job, kernel32.CloseHandle


def _windows_user_cpu_seconds(process: subprocess.Popen[str]) -> float | None:
    """Read a Windows child user-CPU clock without adding a native dependency."""
    if os.name != "nt" or not hasattr(process, "_handle"):
        return None
    import ctypes
    from ctypes import wintypes

    class FileTime(ctypes.Structure):
        _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE, ctypes.POINTER(FileTime),
                                         ctypes.POINTER(FileTime), ctypes.POINTER(FileTime),
                                         ctypes.POINTER(FileTime)]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    created, exited, kernel, user = FileTime(), FileTime(), FileTime(), FileTime()
    if not kernel32.GetProcessTimes(wintypes.HANDLE(process._handle), ctypes.byref(created),
                                    ctypes.byref(exited), ctypes.byref(kernel), ctypes.byref(user)):
        return None
    ticks = (int(user.high) << 32) | int(user.low)
    return ticks / 10_000_000


def _windows_working_set_bytes(process: subprocess.Popen[str]) -> int | None:
    """Read the Windows child working set without a third-party process library."""
    if os.name != "nt" or not hasattr(process, "_handle"):
        return None
    import ctypes
    from ctypes import wintypes

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE,
                                           ctypes.POINTER(ProcessMemoryCounters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(wintypes.HANDLE(process._handle), ctypes.byref(counters), counters.cb):
        return None
    return int(counters.WorkingSetSize)


def _start_windows_resource_watchdog(process: subprocess.Popen[str], cpu_seconds: int,
                                     memory_bytes: int, stopped: threading.Event,
                                     cpu_exceeded: list[bool], memory_exceeded: list[bool]
                                     ) -> threading.Thread | None:
    if os.name != "nt" or not hasattr(process, "_handle"):
        return None

    def watch() -> None:
        while not stopped.wait(0.05):
            used = _windows_user_cpu_seconds(process)
            if used is not None and used >= cpu_seconds:
                cpu_exceeded.append(True)
                _kill_process(process)
                return
            working_set = _windows_working_set_bytes(process)
            if working_set is not None and working_set >= memory_bytes:
                memory_exceeded.append(True)
                _kill_process(process)
                return

    thread = threading.Thread(target=watch, name="docplatform-worker-cpu-watchdog", daemon=True)
    thread.start()
    return thread


def run_isolated(kind: str, payload: dict[str, Any], *, timeout_seconds: int,
                 cpu_seconds: int, memory_bytes: int, max_output_bytes: int) -> dict[str, Any]:
    envelope = json.dumps({"kind": kind, "payload": payload}, ensure_ascii=False)
    environment = _sandbox_environment()
    environment["DOCPLATFORM_WORKER_CHILD"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    command = [sys.executable, "-m", "app.worker_child", str(cpu_seconds), str(memory_bytes),
               str(max_output_bytes)]
    options: dict[str, Any] = {"cwd": Path(__file__).resolve().parents[1], "env": environment,
                               "stdin": subprocess.PIPE, "stdout": subprocess.PIPE,
                               "stderr": subprocess.PIPE, "text": True, "encoding": "utf-8"}
    if os.name == "posix":
        options["start_new_session"] = True
    elif hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    process = subprocess.Popen(command, **options)
    try:
        windows_job = _assign_windows_job_limits(process, cpu_seconds, memory_bytes)
    except Exception:
        _kill_process(process)
        process.communicate()
        raise
    cpu_stopped = threading.Event()
    cpu_exceeded: list[bool] = []
    memory_exceeded: list[bool] = []
    cpu_watchdog = _start_windows_resource_watchdog(process, cpu_seconds, memory_bytes,
                                                     cpu_stopped, cpu_exceeded, memory_exceeded)
    try:
        try:
            stdout, stderr = process.communicate(envelope, timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            _kill_process(process)
            process.communicate()
            raise WorkerExecutionError("job exceeded the configured wall-time limit") from None
        if cpu_exceeded:
            raise WorkerExecutionError("job exceeded the configured CPU limit")
        if memory_exceeded:
            raise WorkerExecutionError("job exceeded the configured memory limit")
        if len(stdout.encode("utf-8")) > max_output_bytes:
            if process.poll() is None:
                _kill_process(process)
            raise WorkerExecutionError("job output exceeded the configured limit")
        if process.returncode != 0:
            detail = stderr.strip()[:500]
            if not detail:
                try:
                    child_result = json.loads(stdout)
                except json.JSONDecodeError:
                    child_result = {}
                if isinstance(child_result, dict):
                    detail = str(child_result.get("error", ""))[:500]
            detail = detail or "isolated worker failed"
            raise WorkerExecutionError(detail)
        try:
            result = json.loads(stdout)
        except json.JSONDecodeError:
            raise WorkerExecutionError("isolated worker returned invalid JSON") from None
        if not isinstance(result, dict) or result.get("ok") is not True or not isinstance(result.get("result"), dict):
            raise WorkerExecutionError(str(result.get("error", "isolated worker rejected the job"))[:500])
        return result["result"]
    finally:
        cpu_stopped.set()
        if cpu_watchdog is not None:
            cpu_watchdog.join(timeout=1)
        if windows_job is not None:
            _, close_handle = windows_job
            close_handle(windows_job[0])
