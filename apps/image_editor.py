import os
import sys
from typing import Dict, Literal

import numpy as np
import qdarkstyle
from PIL.Image import Image
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QPushButton, QLabel, QComboBox, QGroupBox, \
    QRadioButton, QCheckBox, QTableWidget, QDoubleSpinBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt
from PySide6.QtGui import QPixmap
from PIL import Image as ImageModule

from src.image_editor.effects.blend import BlendMode, BlendImagesEffect
# Import your image effects and effect appliers.
from src.image_editor.effects.color_matrix import ColorMatrixEffect, ColorMatrixPreset
from src.image_editor.effects.grayscale import GrayscaleImageEffect, GrayscaleAlgorithm
from src.image_editor.effects.transform import TransformImageEffect
from src.image_editor.image_analyzer import display_color_distribution
from src.image_editor.image_effect_applier import SingleImageEffectApplier, DoubleImageEffectApplier
from src.image_editor.image_effects import ImageEffectType, SingleImageEffect, ImageEffect
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
        loaded_window = self.ui = loader.load(ui_file)
        ui_file.close()

        self.setCentralWidget(loaded_window.centralWidget())
        self.setWindowTitle(loaded_window.windowTitle())
        self.setFixedWidth(loaded_window.width())
        self.setFixedHeight(loaded_window.height())

        self.images: Dict[Literal['original', 'result', 'blend_left', 'blend_right', 'blend_result'], Image | None] = {
            'original': None,
            'result': None,
            'blend_left': None,
            'blend_right': None,
            'blend_result': None,
        }

        self.single_image_effects: Dict[ImageEffectType, SingleImageEffect] = {
        }

        self.single_image_effect_applier = SingleImageEffectApplier(original=None)
        self.double_image_effect_applier = DoubleImageEffectApplier(left=None, right=None)

        self.image_elements: Dict[
            Literal['original', 'result', 'blend_left', 'blend_right', 'blend_result'], QLabel
        ] = {
            'original': self.findChild(QLabel, 'originalImage_image'),
            'result': self.findChild(QLabel, 'resultImage_image'),
            'blend_left': self.findChild(QLabel, 'blendLeftImage_image'),
            'blend_right': self.findChild(QLabel, 'blendRightImage_image'),
            'blend_result': self.findChild(QLabel, 'blendResultImage_image'),
        }
        self.load_buttons: Dict[
            Literal['original', 'blend_left', 'blend_right'], QPushButton
        ] = {
            'original': self.findChild(QPushButton, 'originalImage_loadButton'),
            'blend_left': self.findChild(QPushButton, 'blendLeftImage_loadButton'),
            'blend_right': self.findChild(QPushButton, 'blendRightImage_loadButton'),
        }
        self.save_buttons: Dict[
            Literal['result', 'blend_result'], QPushButton
        ] = {
            'result': self.findChild(QPushButton, 'resultImage_saveButton'),
            'blend_result': self.findChild(QPushButton, 'blendResultImage_saveButton'),
        }
        self.analyze_buttons: Dict[
            Literal['original', 'result', 'blend_left', 'blend_right', 'blend_result'], QPushButton
        ] = {
            'original': self.findChild(QPushButton, 'originalImage_analyzeButton'),
            'result': self.findChild(QPushButton, 'resultImage_analyzeButton'),
            'blend_left': self.findChild(QPushButton, 'blendLeftImage_analyzeButton'),
            'blend_right': self.findChild(QPushButton, 'blendRightImage_analyzeButton'),
            'blend_result': self.findChild(QPushButton, 'blendResultImage_analyzeButton'),
        }
        for key in ['original', 'blend_left', 'blend_right']:
            self.load_buttons[key].clicked.connect(lambda checked, _key=key: self.on_load_image(_key))
            self.analyze_buttons[key].clicked.connect(lambda checked, _key=key: self.on_analyze_image(_key))
        for key in ['result', 'blend_result']:
            self.save_buttons[key].clicked.connect(lambda checked, _key=key: self.on_save_result_image(_key))
            self.analyze_buttons[key].clicked.connect(lambda checked, _key=key: self.on_analyze_image(_key))

        # Blend input elements
        blend_mode = BlendMode.NORMAL
        self.blend_effect = BlendImagesEffect(blend_mode)
        self.double_image_effect_applier += self.blend_effect
        self.blend_blendMode_select = self.findChild(QComboBox, 'blend_blendMode_select')
        self.blend_blendMode_select.addItems(map(lambda i: i.value, BlendMode))
        self.blend_blendMode_select.setCurrentIndex(blend_mode.index)
        self.blend_blendMode_select.currentIndexChanged.connect(lambda index: self.on_blend_mode_changed(
            BlendMode.for_index(index)
        ))
        self.blend_blendButton = self.findChild(QPushButton, 'blend_blendButton')
        self.blend_blendButton.clicked.connect(lambda: self.update_result_image('blend_result'))

        # Transform input elements
        transform_effect = TransformImageEffect()
        self.single_image_effects[ImageEffectType.TRANSFORM] = transform_effect
        for angle in [0, 90, 180, 270]:
            angle_radio = self.findChild(QRadioButton, f'transform_rotationAngle_{angle}')
            angle_radio.clicked.connect(
                lambda checked, _angle=angle: self.on_transform_effect_changed(rotation=_angle)
            )
        self.transform_flipVertical_checkbox = self.findChild(QCheckBox, 'transform_flipVertical_checkbox')
        self.transform_flipVertical_checkbox.clicked.connect(
            lambda checked: self.on_transform_effect_changed(flip_vertical=checked)
        )
        self.transform_flipHorizontal_checkbox = self.findChild(QCheckBox, 'transform_flipHorizontal_checkbox')
        self.transform_flipHorizontal_checkbox.clicked.connect(
            lambda checked: self.on_transform_effect_changed(flip_horizontal=checked)
        )

        self.transform_group = self.findChild(QGroupBox, 'effectTransformGroup')
        self.transform_group.clicked.connect(
            lambda checked: self.on_toggle_single_effect(ImageEffectType.TRANSFORM, checked)
        )

        # Grayscale input elements
        grayscale_algorithm = GrayscaleAlgorithm.GAMMA
        grayscale_effect = GrayscaleImageEffect(grayscale_algorithm)
        self.single_image_effects[ImageEffectType.GRAYSCALE] = grayscale_effect
        self.grayscale_algorithmSelect = self.findChild(QComboBox, 'grayscale_algorithmSelect')
        self.grayscale_algorithmSelect.addItems(map(lambda i: i.value, GrayscaleAlgorithm))
        self.grayscale_algorithmSelect.setCurrentIndex(grayscale_algorithm.index)
        self.grayscale_algorithmSelect.currentIndexChanged.connect(lambda index: self.on_grayscale_algorithm_changed(
            GrayscaleAlgorithm.for_index(index)
        ))
        self.grayscale_group = self.findChild(QGroupBox, 'effectGrayscaleGroup')
        self.grayscale_group.clicked.connect(
            lambda checked: self.on_toggle_single_effect(ImageEffectType.GRAYSCALE, checked)
        )

        color_matrix_preset = ColorMatrixPreset.IDENTITY
        color_matrix_effect = ColorMatrixEffect(color_matrix_preset.value.matrix)
        self.single_image_effects[ImageEffectType.COLOR_MATRIX] = color_matrix_effect
        self.colorMatrix_table = self.findChild(QTableWidget, 'colorMatrix_table')
        self.color_matrix_spinners = []
        for i in range(4):
            self.color_matrix_spinners.append([])
            for j in range(5):
                spinner = QDoubleSpinBox(
                    decimals=2,
                    minimum=-2,
                    maximum=2,
                    singleStep=.01
                )
                spinner.valueChanged.connect(
                    lambda value, _i=i, _j=j: self.on_color_matrix_table_changed(_i, _j, value)
                )
                self.color_matrix_spinners[i].append(spinner)
                self.colorMatrix_table.setCellWidget(i, j, spinner)
        self.update_color_matrix_table()

        self.color_matrix_preset_select = self.findChild(QComboBox, 'colorMatrix_presetSelect')
        self.color_matrix_preset_select.addItems(map(lambda i: i.value.name, ColorMatrixPreset))
        self.color_matrix_preset_select.setCurrentIndex(color_matrix_preset.index)
        self.color_matrix_preset_select.currentIndexChanged.connect(lambda index: self.on_color_matrix_table_replaced(
            ColorMatrixPreset.for_index(index).value.matrix()
        ))

        self.color_matrix_group = self.findChild(QGroupBox, 'effectColorMatrixGroup')
        self.color_matrix_group.clicked.connect(
            lambda checked: self.on_toggle_single_effect(ImageEffectType.COLOR_MATRIX, checked)
        )

        self.applyAllButton = self.findChild(QPushButton, 'applyAllButton')
        self.applyAllButton.clicked.connect(lambda: self.update_result_image('result'))

    def on_load_image(self,
                      key: Literal['original', 'result', 'blend_left', 'blend_right', 'blend_result'],
                      ):
        print(f'Trying to load image for key {key}')
        # Open a file dialog to choose an image.
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            os.path.expanduser("~"),
            "Image Files (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if file_path:
            if self.analyze_buttons[key] is not None:
                self.analyze_buttons[key].setEnabled(file_path is not None)

            print("Selected file:", file_path)

            original_image = ImageModule.open(file_path)
            self.images[key] = original_image

            match key:
                case 'original':
                    self.single_image_effect_applier.original_image = original_image
                case 'blend_left':
                    self.double_image_effect_applier.left_image = original_image
                case 'blend_right':
                    self.double_image_effect_applier.right_image = original_image
                case _:
                    pass

            pixmap = QPixmap(file_path)
            # Optionally scale the pixmap to fit the display area:
            pixmap = pixmap.scaled(self.image_elements[key].size(), aspectMode=Qt.AspectRatioMode.KeepAspectRatio)
            self.image_elements[key].setPixmap(pixmap)

            match key:
                case 'original':
                    self.update_result_image(key='result')
                case 'blend_left' | 'blend_right':
                    if self.images['blend_left'] is not None and self.images['blend_right'] is not None:
                        self.update_result_image(key='blend_result')


    def on_analyze_image(self, key: Literal['original', 'result', 'blend_left', 'blend_right', 'blend_result']):
        image = self.images[key]
        if image is None:
            print("Image is not loaded properly.")
            return
        display_color_distribution(image)

    def on_save_result_image(self, key: Literal['result', 'blend_result']):
        if self.images[key] is None:
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

        self.images[key].save(file_path)

    def update_result_image(self,
                            key: Literal['result', 'blend_result']
                            ):
        # Update self.ui.resultImage_image. Perhaps save it to temporary image?
        # SingleImageEffectApplier#apply_all_effects() returns a pil image.
        result_image = self.single_image_effect_applier.apply_all_effects() if key == 'result' \
            else self.double_image_effect_applier.apply_all_effects()
        result_temp_path = save_temp_image(result_image)

        try:
            pixmap = QPixmap(result_temp_path)
            pixmap = pixmap.scaled(self.image_elements[key].size(), aspectMode=Qt.AspectRatioMode.KeepAspectRatio)
            self.image_elements[key].setPixmap(pixmap)

            # If you do NOT need to keep the file around, delete it
            os.remove(result_temp_path)

        except Exception as e:
            print("Couldn't set result image.", e)
            self.images[key] = result_image
            self.save_buttons[key].setEnabled(False)
            self.analyze_buttons[key].setEnabled(False)
            if key == 'blend_result':
                self.blend_blendButton.setEnabled(False)
            else:
                self.applyAllButton.setEnabled(False)

        else:
            print("Set result image.")
            self.images[key] = result_image
            self.save_buttons[key].setEnabled(True)
            self.analyze_buttons[key].setEnabled(True)
            if key == 'blend_result':
                self.blend_blendButton.setEnabled(True)
            else:
                self.applyAllButton.setEnabled(True)

    def on_blend_mode_changed(self, blend_mode: BlendMode):
        print(f"Blend mode is now {blend_mode}")
        self.blend_effect.blend_mode = blend_mode

    def on_transform_effect_changed(
            self, rotation: int | None = None,
            flip_vertical: bool | None = None,
            flip_horizontal: bool | None = None
        ):
        if rotation is not None:
            self.single_image_effects[ImageEffectType.TRANSFORM].rotation = rotation
        if flip_vertical is not None:
            self.single_image_effects[ImageEffectType.TRANSFORM].flip_vertical = flip_vertical
        if flip_horizontal is not None:
            self.single_image_effects[ImageEffectType.TRANSFORM].flip_horizontal = flip_horizontal

        print(self.single_image_effects[ImageEffectType.TRANSFORM])

    def on_grayscale_algorithm_changed(self, algorithm: GrayscaleAlgorithm):
        print(f"Grayscale algorithm is now {algorithm}")
        self.single_image_effects[ImageEffectType.GRAYSCALE].algorithm = algorithm

    def on_toggle_single_effect(self, effect_type: ImageEffectType, checked: bool):
        if checked:
            print(f"Effect {effect_type.name} enabled.")
            self.single_image_effect_applier += self.single_image_effects[effect_type]
        else:
            print(f"Effect {effect_type.name} disabled.")
            self.single_image_effect_applier -= self.single_image_effects[effect_type]
        print(self.single_image_effect_applier.effects)

    def on_table_clicked(self):
        print(self.colorMatrix_table.children())

    def update_color_matrix_table(self):
        for i in range(4):
            for j in range(5):
                self.color_matrix_spinners[i][j].setValue(
                    self.single_image_effects[ImageEffectType.COLOR_MATRIX].matrix[i, j]
                )

    def on_color_matrix_table_changed(self, i, j, new_value):
        print(f'Matrix [{i}, {j}] is now {new_value}')
        self.single_image_effects[ImageEffectType.COLOR_MATRIX].matrix[i, j] = new_value
        print(self.single_image_effects[ImageEffectType.COLOR_MATRIX].matrix[i, j])
        pass

    def on_color_matrix_table_replaced(self, new_value):
        print('Setting new color matrix')
        self.single_image_effects[ImageEffectType.COLOR_MATRIX].matrix = np.array(new_value)
        self.update_color_matrix_table()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Apply a dark theme in a couple of lines.
    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyside6'))
    image_editor = ImageEditor()
    image_editor.show()  # Show the loaded UI
    sys.exit(app.exec())
