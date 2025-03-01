import os
import sys

import qdarkstyle
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QPushButton, QLabel, QLineEdit,
    QCheckBox, QRadioButton, QProgressBar
)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from pytubefix import YouTube, Playlist
from pydub import AudioSegment  # For MP3 conversion

from src.util.string_utils import distill_filename


class VideoDownloader(QMainWindow):
    def __init__(self):
        super().__init__()

        # Load the .ui file with QUiLoader
        loader = QUiLoader()
        ui_file = QFile("video_downloader.ui")  # Ensure this file exists
        if not ui_file.open(QFile.ReadOnly):
            print("Unable to open video_downloader.ui")
            sys.exit(-1)
        loaded_window = loader.load(ui_file)
        ui_file.close()

        # Set the loaded UI as the central widget
        self.setCentralWidget(loaded_window.centralWidget())
        self.setWindowTitle(loaded_window.windowTitle())
        self.setFixedSize(loaded_window.size())

        # Find widgets
        self.link_input: QLineEdit = self.findChild(QLineEdit, "linkInput")
        self.choose_dir_button: QPushButton = self.findChild(QPushButton, "chooseDirButton")
        self.save_dir_label: QLabel = self.findChild(QLabel, "saveDirLabel")
        self.download_playlist_check: QCheckBox = self.findChild(QCheckBox, "downloadPlaylistCheck")
        self.radio_video: QRadioButton = self.findChild(QRadioButton, "radioVideo")
        self.radio_audio: QRadioButton = self.findChild(QRadioButton, "radioAudio")
        self.download_button: QPushButton = self.findChild(QPushButton, "downloadButton")
        self.download_progress: QProgressBar = self.findChild(QProgressBar, "downloadProgressBar")

        # Initialize defaults
        self.save_dir = None
        self.link = None
        self.download_progress.setValue(0)

        # Connect signals
        self.link_input.textChanged.connect(lambda text: self.on_change_link(text))
        self.choose_dir_button.clicked.connect(self.on_choose_directory)
        self.download_button.clicked.connect(self.on_download)

    def on_change_link(self, text):
        """ Updates the link variable and checks if the download button should be enabled. """
        self.link = text.strip()
        self.toggle_download_if_ready()

    def on_choose_directory(self):
        """ Allows user to pick a directory to save the downloads. """
        directory = QFileDialog.getExistingDirectory(self, "Choose directory", os.path.expanduser("~"))
        if directory:
            self.save_dir = directory
            self.save_dir_label.setText(directory)
        elif self.save_dir is None:
            self.save_dir_label.setText("Directory not chosen")

        self.toggle_download_if_ready()

    def toggle_download_if_ready(self):
        """ Enables the download button if a link and save directory are selected. """
        is_enabled = bool(self.link) and bool(self.save_dir)
        self.download_button.setEnabled(is_enabled)
        self.download_progress.setEnabled(is_enabled)

    def on_download(self):
        """ Handles the downloading of either a single video or an entire playlist. """
        link = self.link
        if not link:
            print("No link provided.")
            return

        if not self.save_dir:
            print("No save directory chosen.")
            return

        self.download_progress.setValue(0)

        is_playlist = self.download_playlist_check.isChecked()
        mode = "audio" if self.radio_audio.isChecked() else "video"

        if is_playlist:
            success = self.download_playlist(link, mode)
            if not success:
                print("Failed to download playlist. Falling back to single video...")
                self.download_single(link, mode)
        else:
            self.download_single(link, mode)

    def download_single(self, link: str, mode: str):
        """ Downloads a single video in the chosen mode ('video' or 'audio'). """
        try:
            yt = YouTube(link, on_progress_callback=self.on_progress)

            def on_complete_callback(stream, file_path):
                print(f'Download complete of {file_path}')
                if mode == "audio":
                    self.convert_to_mp3(file_path)

            yt.register_on_complete_callback(on_complete_callback)

            if mode == "audio":
                stream = yt.streams.filter(only_audio=True).first()
                if stream:
                    stream.download(output_path=self.save_dir)
            else:
                stream = yt.streams.get_highest_resolution()
                if stream:
                    stream.download(output_path=self.save_dir)

            print("Download complete.")
            self.download_progress.setValue(100)

        except Exception as e:
            print(f"Error downloading single video: {e}")

    def download_playlist(self, link: str, mode: str) -> bool:
        """ Downloads an entire playlist in the chosen mode ('video' or 'audio'). """
        try:
            playlist = Playlist(link)
            videos = playlist.videos
            total_videos = len(videos)

            if total_videos == 0:
                print("No videos found in playlist.")
                return False

            playlist_name = playlist.title or "Playlist"
            playlist_name = distill_filename(playlist_name)
            playlist_dir = os.path.join(self.save_dir, playlist_name)
            os.makedirs(playlist_dir, exist_ok=True)

            for i, yt in enumerate(videos, start=1):
                yt.register_on_progress_callback(self.on_progress)

                def on_complete_callback(stream, file_path):
                    print(f'Download complete of {file_path}')
                    if mode == "audio":
                        self.convert_to_mp3(file_path)

                yt.register_on_complete_callback(on_complete_callback)

                if mode == "audio":
                    stream = yt.streams.filter(only_audio=True).first()
                    if stream:
                        stream.download(output_path=playlist_dir)
                else:
                    stream = yt.streams.get_highest_resolution()
                    if stream:
                        stream.download(output_path=playlist_dir)

                self.download_progress.setValue(int(i / total_videos * 100))

            print("Playlist download complete.")
            return True

        except Exception as e:
            print(f"Error downloading playlist: {e}")
            return False

    def convert_to_mp3(self, filename: str):
        """ Converts a downloaded audio file (e.g., .mp4) to MP3 format. """
        try:
            if not filename.lower().endswith(".m4a"):
                print(f"Skipping conversion for {filename} (not an M4A).")
                return

            new_filename = os.path.splitext(filename)[0] + ".mp3"

            audio = AudioSegment.from_file(filename, format="m4a")
            audio.export(new_filename, format="mp3", bitrate="192k")

            print(f"Converted {filename} to {new_filename}")
            os.remove(filename)  # Remove the original MP4 file

        except Exception as e:
            print(f"Error converting {filename} to MP3: {e}")

    def on_progress(self, stream, chunk, bytes_remaining):
        """ Updates the progress bar as the file downloads. """
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining
        percentage = int(bytes_downloaded / total_size * 100)
        self.download_progress.setValue(percentage)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyside6'))

    window = VideoDownloader()
    window.show()
    sys.exit(app.exec())
