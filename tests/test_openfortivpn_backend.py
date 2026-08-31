import subprocess

import pytest

from services.openfortivpn_backend import SUDO, OpenfortivpnBackend


class FakeProcess:
    """Simula subprocess.Popen: .pid fixo e .poll() controlável pelo teste.

    poll_result None = ainda rodando; 0 = terminou com sucesso; != 0 = falhou.
    """

    def __init__(self, pid=4242, poll_result=None):
        self.pid = pid
        self.poll_result = poll_result

    def poll(self):
        return self.poll_result


class FakeCommandRunner:
    def __init__(self, is_running=True, popen_result=None):
        self.popen_calls = []
        self.run_calls = []
        self._is_running = is_running
        self._popen_result = popen_result
        self.procs = []

    def popen(self, args, **kwargs):
        self.popen_calls.append((args, kwargs))
        proc = self._popen_result or FakeProcess(pid=4242)
        self.procs.append(proc)
        return proc

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
    # issue #4: stdin fechado para evitar bloqueio esperando entrada interativa
    # via sudo quando a GUI não fornece nenhuma.
    assert kwargs["stdin"] == subprocess.DEVNULL


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


def test_poll_outcome_para_pid_desconhecido_retorna_none(tmp_path):
    runner = FakeCommandRunner()
    backend = OpenfortivpnBackend(log_path=str(tmp_path / "log.txt"), command_runner=runner)

    assert backend.poll_outcome(1234) is None


def test_poll_outcome_processo_ainda_rodando_retorna_none(tmp_path):
    runner = FakeCommandRunner()
    backend = OpenfortivpnBackend(log_path=str(tmp_path / "log.txt"), command_runner=runner)

    pid = backend.start("/etc/openfortivpn/matriz.conf")
    # ainda não terminou (poll_result continua None)

    assert backend.poll_outcome(pid) is None


def test_poll_outcome_processo_terminado_com_sucesso(tmp_path):
    runner = FakeCommandRunner()
    backend = OpenfortivpnBackend(log_path=str(tmp_path / "log.txt"), command_runner=runner)

    pid = backend.start("/etc/openfortivpn/matriz.conf")
    runner.procs[0].poll_result = 0

    outcome = backend.poll_outcome(pid)

    assert outcome is not None
    assert outcome.succeeded is True
    assert outcome.exit_code == 0


def test_poll_outcome_processo_falhou_traz_motivo_do_log(tmp_path):
    log_path = tmp_path / "log.txt"
    runner = FakeCommandRunner()
    backend = OpenfortivpnBackend(log_path=str(log_path), command_runner=runner)

    pid = backend.start("/etc/openfortivpn/matriz.conf")
    # simula a saída que o processo openfortivpn teria escrito no log
    with open(log_path, "a") as f:
        f.write("sudo: a password is required\n")
    runner.procs[0].poll_result = 1

    outcome = backend.poll_outcome(pid)

    assert outcome is not None
    assert outcome.succeeded is False
    assert outcome.exit_code == 1
    assert outcome.message == "sudo negou permissão"


def test_poll_outcome_falha_sem_pista_reconhecida_usa_ultima_linha_do_log(tmp_path):
    log_path = tmp_path / "log.txt"
    runner = FakeCommandRunner()
    backend = OpenfortivpnBackend(log_path=str(log_path), command_runner=runner)

    pid = backend.start("/etc/openfortivpn/matriz.conf")
    with open(log_path, "a") as f:
        f.write("Could not connect to gateway\n")
    runner.procs[0].poll_result = 1

    outcome = backend.poll_outcome(pid)

    assert outcome.message == "Could not connect to gateway"


def test_is_running_com_pid_conhecido_consulta_o_processo_rastreado(tmp_path):
    runner = FakeCommandRunner()
    backend = OpenfortivpnBackend(log_path=str(tmp_path / "log.txt"), command_runner=runner)

    pid = backend.start("/etc/openfortivpn/matriz.conf")

    assert backend.is_running(pid) is True

    runner.procs[0].poll_result = 0

    assert backend.is_running(pid) is False
    # não deve cair no pgrep genérico quando o pid é conhecido
    assert runner.run_calls == []
