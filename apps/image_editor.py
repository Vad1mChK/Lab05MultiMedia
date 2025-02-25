import os
import sys
from typing import Dict

import qdarkstyle
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt
from PySide6.QtGui import QPixmap
from PIL import Image as ImageModule

# Import your image effects and effect appliers.
from src.image_editor.effects.color_matrix import ColorMatrixEffect, presets as color_matrix_presets
from src.image_editor.effects.grayscale import GrayscaleImageEffect
from src.image_editor.effects.transform import TransformImageEffect
from src.image_editor.image_effect_applier import SingleImageEffectApplier, DoubleImageEffectApplier
from src.image_editor.image_effects import ImageEffectType, SingleImageEffect
from src.util.io_utils import save_temp_image


class ImageEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        # Load the UI file designed in QtDesigner.
        loader = QUiLoader()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ui_file_path = os.path.join(script_dir, "image_editor.ui")
        ui_file = QFile(ui_file_path)
        if not ui_file.open(QFile.ReadOnly):
            print("Unable to open image_editor.ui")
            sys.exit(-1)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.single_image_effect_applier = SingleImageEffectApplier(original=None)
        self.double_image_effect_applier = DoubleImageEffectApplier(left=None, right=None)

        # Connect the load button.
        self.ui.originalImage_loadButton.clicked.connect(self.on_load_original_image)
        self.ui.resultImage_saveButton.clicked.connect(self.on_save_single_result_image)

    def on_load_original_image(self):
        # Open a file dialog to choose an image.
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            os.path.expanduser("~"),
            "Image Files (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        self.ui.originalImage_analyzeButton.setEnabled(file_path is not None)
        if file_path:
            print("Selected file:", file_path)
            self.single_image_effect_applier = SingleImageEffectApplier(original=ImageModule.open(file_path))
            # Assuming your .ui has a QLabel with objectName 'originalImage_display'
            pixmap = QPixmap(file_path)
            # Optionally scale the pixmap to fit the display area:
            pixmap = pixmap.scaled(self.ui.originalImage_image.size(), aspectMode=Qt.AspectRatioMode.KeepAspectRatio)
            self.ui.originalImage_image.setPixmap(pixmap)
            # You might also want to update your effect applier with the loaded image.
            # For example:
            # from PIL import Image as PILImage

            self.update_single_result_image()

    def on_analyze_original_image(self):
        pass

    def on_save_single_result_image(self):
        if self.result_image is None:
            print("No image to save")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Image",
            os.path.expanduser("~"),
            "Image Files (*.png)"
        )

        if not file_path:
            print("Path to save image was not specified")
            return

        self.result_image.save(file_path)

    def update_single_result_image(self):
        # Update self.ui.resultImage_image. Perhaps save it to temporary image?
        # SingleImageEffectApplier#apply_all_effects() returns a pil image.
        result_image = self.single_image_effect_applier.apply_all_effects()
        result_temp_path = save_temp_image(result_image)

        try:
            pixmap = QPixmap(result_temp_path)
            pixmap = pixmap.scaled(self.ui.resultImage_image.size(), aspectMode=Qt.AspectRatioMode.KeepAspectRatio)
            self.ui.resultImage_image.setPixmap(pixmap)

            # If you do NOT need to keep the file around, delete it
            os.remove(result_temp_path)

        except Exception as e:
            print("Couldn't set result image.", e)
            self.result_image = None
            self.ui.resultImage_analyzeButton.setEnabled(False)
            self.ui.resultImage_saveButton.setEnabled(False)

        else:
            print("Set result image.")
            self.result_image = result_image
            self.ui.resultImage_analyzeButton.setEnabled(True)
            self.ui.resultImage_saveButton.setEnabled(True)


if __name__ == '__main__':
    # Initialize effect appliers (if needed elsewhere in your code).

    single_image_effects: Dict[ImageEffectType, SingleImageEffect] = {
        ImageEffectType.TRANSFORM: TransformImageEffect(),
        ImageEffectType.GRAYSCALE: GrayscaleImageEffect(),
        ImageEffectType.COLOR_MATRIX: ColorMatrixEffect(color_matrix_presets['Identity']),
    }

    app = QApplication(sys.argv)
    # Apply a dark theme in a couple of lines.
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyside6'))
    image_editor = ImageEditor()
    image_editor.ui.show()  # Show the loaded UI
    sys.exit(app.exec())
