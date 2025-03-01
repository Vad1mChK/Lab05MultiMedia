import os
import sys
import cv2
import time
import threading
import subprocess
import tempfile
import signal

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout,
    QWidget, QFileDialog, QSlider, QHBoxLayout
)
from PySide6.QtCore import QTimer, Qt, QSize
from PySide6.QtGui import QImage, QPixmap

from pydub import AudioSegment
import qdarkstyle


class VideoPlayer(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OpenCV + pydub Video Player with Seek/Pause/Stop")
        self.setGeometry(100, 100, 800, 600)

        # Video display
        self.video_label = QLabel("Video will be displayed here")
        self.video_label.setAlignment(Qt.AlignCenter)

        # Control buttons
        self.load_button = QPushButton("Load Video")
        self.load_button.clicked.connect(self.load_video)

        self.play_button = QPushButton("Play")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play_video)

        self.pause_button = QPushButton("Pause")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.pause_video)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_video)

        # Seek slider (in milliseconds)
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setEnabled(False)
        self.seek_slider.sliderReleased.connect(self.seek_video)

        # Volume slider (UI only)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)

        # We'll store the frame processing delay measured on the first frame.
        self.frame_processing_delay = None

        # Layouts
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.video_label)
        main_layout.addWidget(self.seek_slider)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.volume_slider)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

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

    def load_video(self) -> None:
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
        # Only update offset if it hasn't been set (e.g., initial playback)
        if self.offset == 0:
            self.offset = self.get_current_offset()
        self.start_audio_from_offset(self.offset)
        self.frame_processing_delay = None
        self.update_frame()

    def update_frame(self) -> None:
        if not self.playing or self.cap is None:
            return

        start_time = time.time()
        ret, frame = self.cap.read()
        if not ret:
            self.stop_video()
            return

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb_frame.data, self.video_width, self.video_height,
                      self.video_width * 3, QImage.Format_RGB888)
        # Scale the image to the pre-calculated target size.
        self.video_label.setPixmap(QPixmap.fromImage(qimg).scaled(
            self.target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # Update the global current offset.
        self.offset = self.cap.get(cv2.CAP_PROP_POS_MSEC)
        self.seek_slider.setValue(int(self.offset))

        elapsed = (time.time() - start_time) * 1000  # processing time in ms
        if self.frame_processing_delay is None:
            # Store the processing time of the first frame.
            self.frame_processing_delay = elapsed
            print(f"Initial frame processing delay stored: {self.frame_processing_delay} ms")
        expected_interval = 1000 / self.fps
        # Subtract the stored processing delay from the expected interval.
        delay = max(0, round(expected_interval - self.frame_processing_delay))
        # print(f'fps: {self.fps}, expected_interval: {expected_interval} ms, delay: {delay} ms')
        QTimer.singleShot(delay, self.update_frame)

    def pause_video(self) -> None:
        if not self.playing:
            return
        self.playing = False
        self.kill_audio_process()
        print("Playback paused.")

    def stop_video(self) -> None:
        self.playing = False
        self.kill_audio_process()
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_MSEC, 0)
        self.seek_slider.setValue(0)
        print("Playback stopped.")

    def seek_video(self) -> None:
        self.offset = self.seek_slider.value()  # in ms
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
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyside6'))
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())
