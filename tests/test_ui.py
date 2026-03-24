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


def test_controller_exposes_darkmode_as_default(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ui_module, "ConfigStore", DummyStore)

    controller = AppController(tmp_path)

    assert controller.darkMode is True
    assert controller.selectedProfileData["save_folder_path"] == ""
