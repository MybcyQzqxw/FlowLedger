"""Entry point for FlowLedger. Run with `python src/main.py`."""
import ctypes
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from flowledger.main_window import MainWindow
from flowledger.resources import resource_path


def main() -> int:
    # Own AppUserModelID so Windows groups the taskbar button under FlowLedger's icon
    # instead of the generic Python one.
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FlowLedger.App")
    except (AttributeError, OSError):
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("FlowLedger")
    icon_file = resource_path("favicon.ico")
    if icon_file.exists():
        app.setWindowIcon(QIcon(str(icon_file)))  # title bar, taskbar and every dialog
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
