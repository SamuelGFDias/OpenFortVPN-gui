import subprocess
import time

from core.interfaces.vpn_backend import VpnBackend
from core.models.connect_outcome import ConnectOutcome
from services.command_runner import CommandRunner, SubprocessCommandRunner

SUDO = ["sudo", "-n"]


class OpenfortivpnBackend(VpnBackend):
    def __init__(
        self,
        log_path: str = "/tmp/openfortivpn-gui.log",
        command_runner: CommandRunner | None = None,
    ) -> None:
        self._log_path = log_path
        self._runner = command_runner or SubprocessCommandRunner()

    def start(self, profile_path: str) -> int:
        with open(self._log_path, "a") as f:
            f.write(f"\n--- connect {profile_path} {time.ctime()} ---\n")
            proc = self._runner.popen(
                SUDO + ["openfortivpn", "-c", profile_path],
                stdout=f,
                stderr=f,
                start_new_session=True,
            )
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
        return None
