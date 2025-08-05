import os
import sys
import qdarkstyle
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QPushButton, QLabel, QLineEdit,
    QCheckBox, QRadioButton, QProgressBar, QSizePolicy
)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QThread, Signal
from pytubefix import YouTube, Playlist
from pydub import AudioSegment  # For MP3 conversion

from src.util.string_utils import distill_filename
from src.util.metadata_utils import tag_mp4_file, tag_mp3_file


class CancelledException(Exception):
    pass


class DownloadWorker(QThread):
    progress_update = Signal(int)
    finished = Signal()
    success = Signal()
    error = Signal(str)
    video_name_change = Signal(str)
    video_author_change = Signal(str)

    def __init__(self, link: str, save_dir: str, is_playlist: bool, mode: str, overwrite_metadata: bool = False):
        super().__init__()
        self.link = link
        self.save_dir = save_dir
        self.is_playlist = is_playlist
        self.mode = mode
        self.is_cancelled = False
        self.overwrite_metadata = overwrite_metadata

    def run(self):
        try:
            if self.is_playlist:
                playlist = Playlist(self.link)
                if not playlist.videos:
                    print("No videos found in playlist. Falling back to single video download.")
                    self.download_single(self.link, self.mode)
                else:
                    success = self.download_playlist(self.link, self.mode)
                    if not success:
                        print("Playlist download failed. Falling back to single video download.")
                        self.download_single(self.link, self.mode)
            else:
                self.download_single(self.link, self.mode)
            self.success.emit()
        except Exception as e:
            self.error.emit(str(e))
            return
        # finally:
        #     self.finished.emit()

    def on_progress(self, stream, chunk, bytes_remaining):
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining
        percentage = int(bytes_downloaded / total_size * 100)
        self.progress_update.emit(percentage)

    def cancel(self):
        self.error.emit('Download cancelled by user.')
        self.terminate()  # This approach is highly discouraged as it stops immediately without cleanup

    def download_single(self, link: str, mode: str):
        yt = YouTube(link, on_progress_callback=self.on_progress)

        # --- 1 · download ---------------------------------------------------------
        if mode == "audio":
            stream = yt.streams.filter(only_audio=True).first()
        else:
            stream = yt.streams.get_highest_resolution()

        if not stream:
            raise ValueError(f"{mode.capitalize()} stream not available.")

        file_path = stream.download(output_path=self.save_dir)  # <── returns AFTER writer closes
        self.progress_update.emit(100)

        # --- 2 · post-processing --------------------------------------------------
        if mode == "audio":
            mp3_file = self.convert_to_mp3(file_path)  # ffmpeg runs, exits → handle freed
            if mp3_file and self.overwrite_metadata:
                tag_mp3_file(mp3_file, title=yt.title, author=yt.author)
            # Safe to delete now – no handle left open
            try:
                os.remove(file_path)
            except PermissionError:
                print(f"Cannot delete the source because ffmpeg still holds it: {file_path}")
        else:
            if self.overwrite_metadata:
                tag_mp4_file(file_path,
                             title=yt.title,
                             author=yt.author,
                             date=yt.publish_date)

    def download_playlist(self, link: str, mode: str) -> bool:
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

            self.video_name_change.emit(yt.title)
            self.video_author_change.emit(yt.author)

            if mode == "audio":
                stream = yt.streams.filter(only_audio=True).first()
            else:
                stream = yt.streams.get_highest_resolution()

            if not stream:
                print(f"Stream {i} not available for {yt.watch_url}.")
                continue

            file_path = stream.download(output_path=playlist_dir)

            if mode == "audio":
                mp3_file = self.convert_to_mp3(file_path)
                if mp3_file:
                    if self.overwrite_metadata:
                        tag_mp3_file(mp3_file, title=yt.title, author=yt.author)
                    try:
                        os.remove(file_path)
                    except PermissionError:
                        print(f"Cannot delete the source because ffmpeg still holds it: {file_path}.")
            else:
                if self.overwrite_metadata:
                    tag_mp4_file(file_path, title=yt.title, author=yt.author, date=yt.publish_date)

            progress = int(i / total_videos * 100)
            self.progress_update.emit(progress)

        print("Playlist download complete.")
        return True

    def convert_to_mp3(self, filename: str) -> str:
        try:
            if not filename.lower().endswith(".m4a"):
                print(f"Skipping conversion for {filename} (not an M4A).")
                return
            new_filename = os.path.splitext(filename)[0] + ".mp3"
            audio = AudioSegment.from_file(filename, format="m4a")
            audio.export(new_filename, format="mp3", bitrate="192k")
            print(f"Converted {filename} -> {new_filename}")
            return new_filename
        except Exception as e:
            print(f"Error converting {filename} to MP3: {e}")
            return None


class VideoDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        loader = QUiLoader()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ui_file_path = os.path.join(script_dir, "video_downloader.ui")
        ui_file = QFile(ui_file_path)  # Ensure this file exists
        if not ui_file.open(QFile.ReadOnly):
            print("Unable to open video_downloader.ui")
            sys.exit(-1)
        loaded_window = loader.load(ui_file)
        ui_file.close()

        self.setCentralWidget(loaded_window.centralWidget())
        self.setWindowTitle(loaded_window.windowTitle())
        self.setFixedSize(loaded_window.size())

        # Find widgets.
        self.link_input: QLineEdit = self.findChild(QLineEdit, "linkInput")
        self.choose_dir_button: QPushButton = self.findChild(QPushButton, "chooseDirButton")
        self.save_dir_label: QLabel = self.findChild(QLabel, "saveDirLabel")
        self.download_playlist_check: QCheckBox = self.findChild(QCheckBox, "downloadPlaylistCheck")
        self.radio_video: QRadioButton = self.findChild(QRadioButton, "radioVideo")
        self.radio_audio: QRadioButton = self.findChild(QRadioButton, "radioAudio")
        self.download_button: QPushButton = self.findChild(QPushButton, "downloadButton")
        self.download_progress: QProgressBar = self.findChild(QProgressBar, "downloadProgressBar")

        self.video_name_label: QLabel = self.findChild(QLabel, "videoNameLabel")
        self.video_author_label: QLabel = self.findChild(QLabel, "videoAuthorLabel")
        self.overwrite_metadata_check: QCheckBox = self.findChild(QCheckBox, "overwriteMetadataCheck")

        self.downloading = False

        self.save_dir = None
        self.link = None
        self.download_progress.setValue(0)

        # Connect signals.
        self.link_input.textChanged.connect(lambda text: self.on_change_link(text))
        self.choose_dir_button.clicked.connect(self.on_choose_directory)
        self.download_button.clicked.connect(self.on_click_download_button)

        self.worker = None

    def on_change_link(self, text):
        self.link = text.strip()
        self.toggle_download_if_ready()

    def on_choose_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Choose directory", os.path.expanduser("~"))
        if directory:
            self.save_dir = directory
            self.save_dir_label.setText(directory)
        elif self.save_dir is None:
            self.save_dir_label.setText("Directory not chosen")
        self.toggle_download_if_ready()

    def toggle_download_if_ready(self):
        is_enabled = bool(self.link) and bool(self.save_dir)
        self.download_button.setEnabled(is_enabled)
        self.download_progress.setEnabled(is_enabled)

    def on_click_download_button(self):
        self.downloading = not self.downloading
        self.update_download_button_text()
        if self.downloading:
            self.on_download()
        else:
            self.on_cancel_download()

    def update_download_button_text(self):
        self.download_button.setText('Cancel' if self.downloading else 'Download')

    def update_video_name_label(self, text: str, is_error: bool = False, is_video_name: bool = False):
        self.video_name_label.setText(text)
        font = self.video_name_label.font()
        font.setBold(is_video_name)
        font.setItalic(is_error)
        self.video_name_label.setFont(font)

    def update_video_author_label(self, text: str = "", is_visible: bool = True):
        self.video_author_label.setText(text)
        self.video_author_label.setVisible(is_visible)
        self.video_author_label.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            (QSizePolicy.Policy.Preferred if is_visible else QSizePolicy.Policy.Ignored)
        )

    def on_download_success(self):
        print("Download succeeded.")
        self.update_video_name_label('Download completed.')
        self.update_video_author_label(is_visible=False)

    def on_download_error(self, err):
        print("Download error:", err)
        self.update_video_name_label(f'Download error: {err}', is_error=True)
        self.update_video_author_label(is_visible=False)

    def on_download_finished(self):
        print("Download finished")
        self.toggle_download_if_ready()
        self.downloading = False
        self.update_download_button_text()

    def on_cancel_download(self):
        print("Cancelling download")
        if self.worker is None:
            raise ValueError("Worker not initialized.")
        self.worker.cancel()

    def on_download(self):
        link = self.link
        if not link:
            print("No link provided.")
            return
        if not self.save_dir:
            print("No save directory chosen.")
            return

        # self.download_button.setEnabled(False)
        self.download_progress.setValue(0)
        is_playlist = self.download_playlist_check.isChecked()
        mode = "audio" if self.radio_audio.isChecked() else "video"
        do_overwrite_metadata = self.overwrite_metadata_check.isChecked()

        # Create and start the worker thread.
        self.worker = DownloadWorker(
            link, self.save_dir, is_playlist, mode,
            overwrite_metadata=do_overwrite_metadata
        )
        self.worker.progress_update.connect(self.download_progress.setValue)
        self.worker.error.connect(self.on_download_error)
        self.worker.success.connect(self.on_download_success)
        self.worker.finished.connect(self.on_download_finished)
        self.worker.video_name_change.connect(
            lambda video_name: self.update_video_name_label(video_name, is_video_name=True))
        self.worker.video_author_change.connect(
            lambda video_author: self.update_video_author_label(video_author)
        )
        self.worker.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyside6'))
    window = VideoDownloader()
    window.show()
    sys.exit(app.exec())
