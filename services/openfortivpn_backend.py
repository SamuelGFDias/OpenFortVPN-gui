import os
import subprocess
import time

from core.interfaces.vpn_backend import VpnBackend
from core.models.connect_outcome import ConnectOutcome
from services.command_runner import CommandRunner, SubprocessCommandRunner
from services.runtime_paths import resolve_runtime_dir

SUDO = ["sudo", "-n"]
_LOG_TAIL_BYTES = 2000


class OpenfortivpnBackend(VpnBackend):
    def __init__(
        self,
        log_path: str | None = None,
        command_runner: CommandRunner | None = None,
    ) -> None:
        self._log_path = log_path or os.path.join(resolve_runtime_dir(), "openfortivpn.log")
        self._runner = command_runner or SubprocessCommandRunner()
        self._processes: dict[int, subprocess.Popen] = {}

    def start(self, profile_path: str) -> int:
        with open(self._log_path, "a") as f:
            f.write(f"\n--- connect {profile_path} {time.ctime()} ---\n")
            proc = self._runner.popen(
                SUDO + ["openfortivpn", "-c", profile_path],
                stdin=subprocess.DEVNULL,
                stdout=f,
                stderr=f,
                start_new_session=True,
            )
        self._processes[proc.pid] = proc
        return proc.pid

    def stop(self, pid: int | None) -> None:
        if pid is not None:
            self._runner.run(
                SUDO + ["kill", "-TERM", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        self._runner.run(
            SUDO + ["pkill", "-x", "openfortivpn"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def is_running(self, pid: int | None) -> bool:
        if pid is not None and pid in self._processes:
            return self._processes[pid].poll() is None
        try:
            self._runner.run(
                ["pgrep", "-x", "openfortivpn"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def poll_outcome(self, pid: int) -> ConnectOutcome | None:
        proc = self._processes.get(pid)
        if proc is None:
            return None
        exit_code = proc.poll()
        if exit_code is None:
            return None
        self._processes.pop(pid, None)
        if exit_code == 0:
            return ConnectOutcome(succeeded=True, exit_code=0)
        return ConnectOutcome(succeeded=False, exit_code=exit_code, message=self._tail_log_reason())

    def _tail_log_reason(self) -> str | None:
        try:
            with open(self._log_path, "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - _LOG_TAIL_BYTES))
                tail = f.read().decode(errors="replace")
        except OSError:
            return None
        lines = [line.strip() for line in tail.splitlines() if line.strip()]
        if not lines:
            return None
        last = lines[-1]
        lowered = last.lower()
        if "password is required" in lowered or ("sudo" in lowered and "not allowed" in lowered):
            return "sudo negou permissão"
        return last[:120]
