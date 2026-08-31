import subprocess
from typing import Protocol


class CommandRunner(Protocol):
    def popen(self, args: list[str], **kwargs) -> subprocess.Popen: ...
    def run(self, args: list[str], **kwargs) -> subprocess.CompletedProcess: ...


class SubprocessCommandRunner:
    def popen(self, args: list[str], **kwargs) -> subprocess.Popen:
        return subprocess.Popen(args, **kwargs)

    def run(self, args: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.run(args, **kwargs)
