from services.json_theme_settings_store import JsonThemeSettingsStore


def test_selected_theme_round_trip(tmp_path):
    store = JsonThemeSettingsStore(settings_path=str(tmp_path / "theme.json"))

    store.save_selected_theme("dark")

    assert store.load_selected_theme() == "dark"


def test_load_selected_theme_retorna_none_se_arquivo_nao_existe(tmp_path):
    store = JsonThemeSettingsStore(settings_path=str(tmp_path / "nao_existe.json"))

    assert store.load_selected_theme() is None
