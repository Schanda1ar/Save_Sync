import sys
from pathlib import Path

def _is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _resource_root() -> Path:
    if _is_frozen():
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return Path(__file__).resolve().parent


def _app_root() -> Path:
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


ROOT_DIR = _resource_root()
APP_DIR = _app_root()
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from backend.ui import AppController


def _icon_path() -> Path:
    return ROOT_DIR / "src" / "icon" / "icon.ico"


def main() -> int:
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Save Sync")
    app.setOrganizationName("Save Sync")
    app.setWindowIcon(QIcon(str(_icon_path())))

    controller = AppController(APP_DIR)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("controller", controller)
    qml_path = ROOT_DIR / "src" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))

    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
