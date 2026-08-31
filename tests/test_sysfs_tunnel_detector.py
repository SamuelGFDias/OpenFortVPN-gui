from services.sysfs_tunnel_detector import SysfsTunnelDetector


def _make_net_dir(tmp_path, names):
    for name in names:
        (tmp_path / name).mkdir()
    return str(tmp_path)


def test_snapshot_retorna_apenas_interfaces_tun_ppp(tmp_path):
    net_dir = _make_net_dir(tmp_path, ["tun0", "ppp0", "eth0"])
    detector = SysfsTunnelDetector(net_dir=net_dir)

    snapshot = detector.snapshot()

    assert snapshot == frozenset({"tun0", "ppp0"})


def test_snapshot_sem_interfaces_relevantes_retorna_vazio(tmp_path):
    net_dir = _make_net_dir(tmp_path, ["eth0", "lo"])
    detector = SysfsTunnelDetector(net_dir=net_dir)

    assert detector.snapshot() == frozenset()


def test_detect_new_interface_ignora_baseline_recebido(tmp_path):
    net_dir = _make_net_dir(tmp_path, ["tun0", "eth0"])
    detector = SysfsTunnelDetector(net_dir=net_dir)

    # Mesmo passando um baseline que já contém a interface existente, o método
    # replica o bug legado (issue #1) e retorna a interface mesmo assim.
    resultado = detector.detect_new_interface(baseline=frozenset({"tun0"}))

    assert resultado == "tun0"


def test_detect_new_interface_sem_interfaces_retorna_none(tmp_path):
    net_dir = _make_net_dir(tmp_path, ["eth0"])
    detector = SysfsTunnelDetector(net_dir=net_dir)

    assert detector.detect_new_interface(baseline=frozenset()) is None


def test_is_interface_present_true_quando_existe(tmp_path):
    net_dir = _make_net_dir(tmp_path, ["tun0"])
    detector = SysfsTunnelDetector(net_dir=net_dir)

    assert detector.is_interface_present("tun0") is True


def test_is_interface_present_false_quando_nao_existe(tmp_path):
    net_dir = _make_net_dir(tmp_path, ["tun0"])
    detector = SysfsTunnelDetector(net_dir=net_dir)

    assert detector.is_interface_present("ppp0") is False


def test_snapshot_com_diretorio_inexistente_retorna_vazio(tmp_path):
    detector = SysfsTunnelDetector(net_dir=str(tmp_path / "nao-existe"))

    assert detector.snapshot() == frozenset()
