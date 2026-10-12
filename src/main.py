"""Entry point for FlowLedger. Run with `python src/main.py`."""
import sys

from PySide6.QtWidgets import QApplication

from flowledger.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("FlowLedger")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
