# main.py

import sys
import qdarktheme
from PyQt5.QtWidgets import QApplication
from controller.main_controller import MainController
from view.main_window import MainWindow
from logging_config import setup_logging

def main():
    setup_logging()
    app = QApplication(sys.argv)
    qdarktheme.setup_theme()

    controller = MainController()
    window = MainWindow(controller)
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
