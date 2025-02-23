from abc import ABC, abstractmethod
from enum import Enum
from typing import Literal

from PIL.Image import Image

from src.image_analyzer.transform import transform_image


class ImageEffectType(Enum):
    TRANSFORM = 0  # Rotate 0/90/180/270 or mirror
    GRAYSCALE = 1  # Grayscale using one of the algorithms
    NORMALIZE = 2  # Normalize colors to (0..1) range (alpha unaffected)
    COLOR_MATRIX = 3  # Linear color manipulations using a 4x5 matrix
    BLEND = 4  # Blend 2 images


class ImageEffect(ABC):
    def __init__(self, effect_type: ImageEffectType):
        self.effect_type = effect_type


class SingleImageEffect(ImageEffect, ABC):
    @abstractmethod
    def apply(self, image: Image) -> Image:
        pass


class TransformImageEffect(SingleImageEffect):
    def __init__(self,
                 rotation: Literal[0, 90, 180, 270] = 0,
                 flip_horizontal: bool = False,
                 flip_vertical: bool = False,):
        super().__init__(effect_type=ImageEffectType.TRANSFORM)
        self._rotation = rotation
        self._flip_horizontal = flip_horizontal
        self._flip_vertical = flip_vertical

    def apply(self, image: Image) -> Image:
        return transform_image(image, self._rotation, self._flip_horizontal, self._flip_vertical)

    def __repr__(self):
        return f'TransformImageEffect(rotation={self._rotation}, flip_horizontal={self._flip_horizontal}, flip_vertical={self._flip_vertical})'


class DoubleImageEffect(ImageEffect, ABC):
    @abstractmethod
    def apply(self, left: Image, right: Image) -> Image:
        pass


class ImageEffectError(Exception):
    pass
