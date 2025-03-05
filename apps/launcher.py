import os
import sys
import subprocess

import qdarkstyle
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

class Launcher(QMainWindow):
    def __init__(self):
        super().__init__()

        # Use QUiLoader to load the UI file.
        loader = QUiLoader()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ui_file_path = os.path.join(script_dir, "launcher.ui")
        ui_file = QFile(ui_file_path)
        if not ui_file.open(QFile.ReadOnly):
            print("Unable to open launcher.ui")
            sys.exit(-1)
        # Load the UI; since the top-level widget in launcher.ui is a QMainWindow,
        # loader.load() returns a QMainWindow instance.
        loaded_window = loader.load(ui_file)
        ui_file.close()

        # Set up our main window by adopting the loaded UI's central widget.
        # This way, our Launcher instance becomes the main window.
        self.setCentralWidget(loaded_window.centralWidget())
        self.setWindowTitle(loaded_window.windowTitle())
        self.setFixedWidth(loaded_window.width())
        self.setFixedHeight(loaded_window.height())

        # Now find the buttons by their object names (as set in QtDesigner).
        self.btnImageEditor = self.findChild(QPushButton, "btnImageEditor")
        self.btnVideoDownloader = self.findChild(QPushButton, "btnVideoDownloader")
        self.btnVideoPlayer = self.findChild(QPushButton, "btnVideoPlayer")

        self.project_root = (os.environ.copy().get("LAB_05_MULTIMEDIA_ROOT") or
                             os.path.dirname(os.path.abspath(__file__)))
        print(f'project_root: {self.project_root}')

        # Connect signals to slots.
        if self.btnImageEditor:
            self.btnImageEditor.clicked.connect(self.launch_image_editor)
        if self.btnVideoDownloader:
            self.btnVideoDownloader.clicked.connect(self.launch_video_downloader)
        if self.btnVideoPlayer:
            self.btnVideoPlayer.clicked.connect(self.launch_video_player)

    def launch_image_editor(self):
        # Launch the image editor as a separate process.
        subprocess.Popen([sys.executable, "-m", "apps.image_editor"], cwd=self.project_root)

    def launch_video_downloader(self):
        # Launch the video downloader as a separate process.
        subprocess.Popen([sys.executable, "-m", "apps.video_downloader"], cwd=self.project_root)

    def launch_video_player(self):
        # Launch the video player as a separate process.
        subprocess.Popen([sys.executable, "-m", "apps.video_player"], cwd=self.project_root)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Apply a dark theme quickly with qdarkstyle.
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyside6'))

    launcher = Launcher()
    launcher.show()  # Show our main launcher window.
    sys.exit(app.exec())
