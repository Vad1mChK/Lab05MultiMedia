import os
import sys
import cv2
import time
import subprocess
import tempfile
import signal
import static_ffmpeg

from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QTimer, Qt, QSize, QFile, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QSlider,
    QWidget, QFileDialog
)

from pydub import AudioSegment
import qdarkstyle

from src.util.string_utils import format_time, truncate_start


class FFmpegDownloadWorker(QThread):
    """
    A background worker thread that downloads/ensures FFmpeg is available
    via static_ffmpeg, and reports its status via signals.
    """
    update_status = Signal(str)
    finished = Signal()

    def run(self):
        try:
            self.update_status.emit("Checking/Downloading FFmpeg...")
            # static_ffmpeg.add_paths() downloads FFmpeg (if necessary) and
            # adds it to PATH. You can also use static_ffmpeg.ensure() if you prefer.
            static_ffmpeg.add_paths()
            self.update_status.emit("FFmpeg is ready.")
        except Exception as e:
            self.update_status.emit(f"Error ensuring FFmpeg: {e}")
        finally:
            # Signal that we're done (successful or otherwise).
            self.finished.emit()


class VideoPlayer(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        # Load the .ui file with QUiLoader
        loader = QUiLoader()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ui_file_path = os.path.join(script_dir, "video_player.ui")
        ui_file = QFile(ui_file_path)  # Ensure this file exists
        if not ui_file.open(QFile.ReadOnly):
            print("Unable to open video_player.ui")
            sys.exit(-1)
        loaded_window = loader.load(ui_file)
        ui_file.close()

        # Set the loaded UI as the central widget
        self.setCentralWidget(loaded_window.centralWidget())
        self.setWindowTitle(loaded_window.windowTitle())
        self.setGeometry(loaded_window.rect())

        # Video display
        self.video_label: QLabel = self.findChild(QLabel, 'videoLabel')
        self.name_label: QLabel = self.findChild(QLabel, 'nameLabel')
        self.time_label: QLabel = self.findChild(QLabel, 'timeLabel')
        self.status_label: QLabel = self.findChild(QLabel, 'statusLabel')  # New label for status messages

        # Control buttons
        self.load_button: QPushButton = self.findChild(QPushButton, 'loadButton')
        self.load_button.clicked.connect(self.load_video)
        self.play_button: QPushButton = self.findChild(QPushButton, 'playButton')
        self.play_button.clicked.connect(self.play_video)
        self.pause_button: QPushButton = self.findChild(QPushButton, 'pauseButton')
        self.pause_button.clicked.connect(self.pause_video)
        self.stop_button: QPushButton = self.findChild(QPushButton, 'stopButton')
        self.stop_button.clicked.connect(self.stop_video)

        # Seek slider (in milliseconds)
        self.seek_slider: QSlider = self.findChild(QSlider, 'seekSlider')
        self.seek_slider.sliderReleased.connect(self.seek_video)

        # Playback state and video properties.
        self.playing = False
        self.fps = 30  # default FPS; updated on video load
        self.video_duration = 0  # in ms
        self.cap = None  # OpenCV video capture
        self.video_width = None
        self.video_height = None
        self.target_size = QSize(0, 0)  # target display size (calculated once)

        # Global current offset (in ms)
        self.offset = 0

        # Audio attributes.
        self.audio = None  # pydub AudioSegment
        self.audio_temp_file = None  # path to exported audio file
        self.audio_process = None  # subprocess.Popen for ffplay

        # Start the thread that ensures FFmpeg is available.
        self.ffmpeg_thread = FFmpegDownloadWorker()
        self.ffmpeg_thread.update_status.connect(self.on_status_update)
        self.ffmpeg_thread.finished.connect(self.on_ffmpeg_ready)
        self.ffmpeg_thread.start()

        # Initially disable playback controls until FFmpeg is ready.
        self.enable_playback_controls(False)

    def on_status_update(self, message: str):
        """
        Slot to update the status label whenever the FFmpegDownloadWorker sends a status.
        """
        self.status_label.setText(message)
        print(f"[FFmpeg Worker] {message}")

    def on_ffmpeg_ready(self):
        """
        Slot called when the FFmpegDownloadWorker has finished ensuring FFmpeg is available.
        """
        # Re-enable load button (or other UI) if necessary.
        self.enable_playback_controls(True)

    def enable_playback_controls(self, enabled: bool):
        """
        Enable or disable all playback-related controls.
        Called initially to disable them until FFmpeg is ready.
        """
        self.load_button.setEnabled(enabled)
        self.play_button.setEnabled(enabled)
        self.pause_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)
        self.seek_slider.setEnabled(enabled)

    def load_video(self) -> None:
        self.stop_video()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Video", os.path.expanduser("~"),
            "Video Files (*.mp4 *.avi *.mkv *.mov)"
        )
        if file_path:
            # Open video file with OpenCV.
            self.cap = cv2.VideoCapture(file_path)
            if not self.cap.isOpened():
                self.video_label.setText("Error opening video file.")
                return

            # Determine FPS.
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.fps = fps if fps > 0 else 30
            print(f"Video FPS: {self.fps}")

            # Read video dimensions once.
            self.video_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.video_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"Video dimensions: {self.video_width}x{self.video_height}")

            # Compute target display dimensions based on video label's width while preserving aspect ratio.
            label_width = self.video_label.width()
            aspect_ratio = self.video_width / self.video_height if self.video_height > 0 else 1
            target_width = label_width
            target_height = int(target_width / aspect_ratio)
            self.target_size = QSize(target_width, target_height)
            print(f"Target display size: {self.target_size.width()}x{self.target_size.height()}")

            # Compute video duration (in ms).
            frame_count = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
            self.video_duration = (frame_count / self.fps) * 1000
            self.seek_slider.setMaximum(int(self.video_duration))
            self.update_name_label(file_path)
            self.update_time_label()
            print(f"Video duration (ms): {self.video_duration}")

            # Load audio using pydub.
            try:
                self.audio = AudioSegment.from_file(file_path)
                print("Audio loaded successfully.")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    self.audio_temp_file = tmp.name
                self.audio.export(self.audio_temp_file, format="wav")
            except Exception as e:
                print(f"Failed to load audio: {e}")
                self.audio = None

            # Enable controls.
            self.play_button.setEnabled(True)
            self.pause_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.seek_slider.setEnabled(True)

    def play_video(self) -> None:
        if self.cap is None:
            return
        self.playing = True

        # Do not reset self.offset if it’s already set (e.g. after a seek)
        if self.offset == 0:
            self.offset = self.get_current_offset()
        self.start_audio_from_offset(self.offset)
        # Record the playback start time and current frame index.
        self.play_start_time = time.time() - (self.offset / 1000.0)
        self.frame_index = int(round(self.offset * self.fps / 1000))

        self.play_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.seek_slider.setEnabled(False)

        self.update_frame()

    def update_frame(self) -> None:
        if not self.playing or self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.stop_video()
            return

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb_frame.data, self.video_width, self.video_height,
                      self.video_width * 3, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qimg).scaled(
            self.target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # Update the global offset and UI.
        self.offset = self.cap.get(cv2.CAP_PROP_POS_MSEC)
        self.seek_slider.setValue(int(self.offset))
        self.update_time_label()

        # Increment frame count.
        self.frame_index += 1
        # Calculate the desired time for this frame.
        target_time = self.play_start_time + (self.frame_index / self.fps)
        current_time = time.time()
        delay = max(0, int((target_time - current_time) * 1000))
        QTimer.singleShot(delay, self.update_frame)

    def update_name_label(self, name: str):
        # Optionally truncate or style the name
        self.name_label.setText(truncate_start(name, limit=48))

    def update_time_label(self):
        self.time_label.setText(
            f'{format_time(int(self.offset))}/{format_time(int(self.video_duration))}'
        )

    def pause_video(self) -> None:
        if not self.playing:
            return
        self.playing = False
        self.kill_audio_process()

        self.play_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.seek_slider.setEnabled(True)

        print("Playback paused.")

    def stop_video(self) -> None:
        self.playing = False
        self.kill_audio_process()
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_MSEC, 0)
        self.seek_slider.setValue(0)
        self.offset = 0

        self.play_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.seek_slider.setEnabled(True)

        print("Playback stopped.")

    def seek_video(self) -> None:
        self.offset = self.seek_slider.value()  # in ms
        self.update_time_label()
        print(f"Seeking to {self.offset} ms")
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_MSEC, self.offset)
        if self.playing:
            self.kill_audio_process()
            self.start_audio_from_offset(self.offset)
            self.update_frame()

    def get_current_offset(self) -> float:
        if self.cap:
            return self.cap.get(cv2.CAP_PROP_POS_MSEC)
        return 0.0

    def start_audio_from_offset(self, offset: float) -> None:
        self.kill_audio_process()
        if self.audio_temp_file is None:
            return
        offset_sec = offset / 1000.0
        cmd = [
            "ffplay", "-nodisp", "-autoexit", "-ss", str(offset_sec),
            "-loglevel", "quiet", self.audio_temp_file
        ]
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
            self.audio_process = subprocess.Popen(cmd, creationflags=creationflags)
        else:
            self.audio_process = subprocess.Popen(cmd, preexec_fn=os.setsid)
        print(f"Audio playback started from offset {offset_sec} sec.")

    def kill_audio_process(self) -> None:
        if self.audio_process is not None:
            try:
                if os.name == "nt":
                    self.audio_process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    os.killpg(os.getpgid(self.audio_process.pid), signal.SIGTERM)
            except Exception as e:
                print(f"Error killing audio process: {e}")
            self.audio_process = None
            print("Audio process killed.")

    def closeEvent(self, event) -> None:
        self.kill_audio_process()
        if self.cap:
            self.cap.release()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Apply dark theme
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyside6'))

    # Instantiate and show the player
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())
