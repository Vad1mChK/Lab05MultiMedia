import os
import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt
import subprocess
import qdarkstyle

class Launcher(QMainWindow):
    def __init__(self):
        super().__init__()
        # Load the UI file designed in QtDesigner.
        loader = QUiLoader()
        ui_file = QFile("launcher.ui")
        if not ui_file.open(QFile.ReadOnly):
            print("Unable to open launcher.ui")
            sys.exit(-1)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

        # Access UI elements by their object names.
        self.ui.btnImageEditor.clicked.connect(self.launch_image_editor)
        self.ui.btnVideoDownloader.clicked.connect(self.launch_video_downloader)
        self.ui.btnVideoPlayer.clicked.connect(self.launch_video_player)

    def launch_image_editor(self):
        # Launch the image editor as a separate process.
        process = subprocess.Popen([sys.executable, "image_editor.py"])

    def launch_video_downloader(self):
        # Launch the video downloader as a separate process.
        subprocess.Popen([sys.executable, "video_downloader.py"])

    def launch_video_player(self):
        # Launch the video player as a separate process.
        subprocess.Popen([sys.executable, "video_player.py"])


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Apply a dark theme in a couple of lines.
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyside6'))

    launcher = Launcher()
    launcher.ui.show()  # Show the loaded UI
    sys.exit(app.exec())
