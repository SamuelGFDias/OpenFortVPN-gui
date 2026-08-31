import subprocess

import pytest

from services.openfortivpn_backend import SUDO, OpenfortivpnBackend


class FakeCompletedProcess:
    def __init__(self, pid=4242):
        self.pid = pid


class FakeCommandRunner:
    def __init__(self, is_running=True):
        self.popen_calls = []
        self.run_calls = []
        self._is_running = is_running

    def popen(self, args, **kwargs):
        self.popen_calls.append((args, kwargs))
        return FakeCompletedProcess(pid=4242)

    def run(self, args, **kwargs):
        self.run_calls.append((args, kwargs))
        if kwargs.get("check") and not self._is_running:
            raise subprocess.CalledProcessError(1, args)
        return subprocess.CompletedProcess(args, 0)


def test_start_monta_comando_certo_e_retorna_pid(tmp_path):
    log_path = str(tmp_path / "log.txt")
    runner = FakeCommandRunner()
    backend = OpenfortivpnBackend(log_path=log_path, command_runner=runner)

    pid = backend.start("/etc/openfortivpn/matriz.conf")

    assert pid == 4242
    assert len(runner.popen_calls) == 1
    args, kwargs = runner.popen_calls[0]
    assert args == SUDO + ["openfortivpn", "-c", "/etc/openfortivpn/matriz.conf"]
    assert kwargs["start_new_session"] is True
    # bug preservado (issue #4): stdin não é definido no Popen
    assert "stdin" not in kwargs


def test_start_escreve_no_log(tmp_path):
    log_path = str(tmp_path / "log.txt")
    runner = FakeCommandRunner()
    backend = OpenfortivpnBackend(log_path=log_path, command_runner=runner)

    backend.start("/etc/openfortivpn/matriz.conf")

    with open(log_path) as f:
        content = f.read()
    assert "connect /etc/openfortivpn/matriz.conf" in content


def test_stop_com_pid_conhecido_sinaliza_o_pid_especifico(tmp_path):
    runner = FakeCommandRunner()
    backend = OpenfortivpnBackend(log_path=str(tmp_path / "log.txt"), command_runner=runner)

    backend.stop(pid=123)

    assert len(runner.run_calls) == 1
    args, kwargs = runner.run_calls[0]
    assert args == SUDO + ["kill", "-TERM", "123"]
    assert kwargs["stdout"] == subprocess.DEVNULL
    assert kwargs["stderr"] == subprocess.DEVNULL


def test_stop_sem_pid_cai_no_fallback_de_matar_por_nome(tmp_path):
    runner = FakeCommandRunner()
    backend = OpenfortivpnBackend(log_path=str(tmp_path / "log.txt"), command_runner=runner)

    backend.stop(pid=None)

    assert len(runner.run_calls) == 1
    args, kwargs = runner.run_calls[0]
    assert args == SUDO + ["pkill", "-x", "openfortivpn"]
    assert kwargs["stdout"] == subprocess.DEVNULL
    assert kwargs["stderr"] == subprocess.DEVNULL


def test_is_running_true_quando_pgrep_sucesso(tmp_path):
    runner = FakeCommandRunner(is_running=True)
    backend = OpenfortivpnBackend(log_path=str(tmp_path / "log.txt"), command_runner=runner)

    assert backend.is_running(None) is True


def test_is_running_false_quando_pgrep_falha(tmp_path):
    runner = FakeCommandRunner(is_running=False)
    backend = OpenfortivpnBackend(log_path=str(tmp_path / "log.txt"), command_runner=runner)

    assert backend.is_running(None) is False


def test_poll_outcome_sempre_retorna_none(tmp_path):
    runner = FakeCommandRunner()
    backend = OpenfortivpnBackend(log_path=str(tmp_path / "log.txt"), command_runner=runner)

    assert backend.poll_outcome(1234) is None
