from pathlib import Path

from backend.models import AppConfig
from backend.ui import AppController
import backend.ui as ui_module


class DummyStore:
    def __init__(self, *args, **kwargs) -> None:
        self.config = AppConfig()

    def load(self) -> AppConfig:
        return self.config

    def save(self, config: AppConfig) -> None:
        self.config = config


class FakeSettings:
    store: dict[str, bool] = {}

    def value(self, key: str, default=None, type=None):
        return self.store.get(key, default)

    def setValue(self, key: str, value) -> None:
        self.store[key] = value

    def sync(self) -> None:
        return None


def test_theme_toggle_persists_between_controller_instances(monkeypatch, tmp_path: Path) -> None:
    FakeSettings.store = {}
    monkeypatch.setattr(ui_module, "ConfigStore", DummyStore)
    monkeypatch.setattr(ui_module, "QSettings", FakeSettings)

    first = AppController(tmp_path)
    assert first.darkMode is False

    first.toggleTheme()
    assert first.darkMode is True

    second = AppController(tmp_path)
    assert second.darkMode is True
