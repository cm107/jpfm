"""Entry point for the JPFM application."""

import sys

from PySide6.QtWidgets import QApplication

from jpfm.services.dictionary_manager import DictionaryManager
from jpfm.ui.main_window import MainWindow
from jpfm.ui.presenter import DictionaryPresenter


def main() -> int:
    app = QApplication(sys.argv)
    main_window = MainWindow()
    manager = DictionaryManager()
    presenter = DictionaryPresenter(main_window, manager, parent=main_window)
    main_window.presenter = presenter
    main_window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
