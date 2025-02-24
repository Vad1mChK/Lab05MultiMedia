from abc import ABC, abstractmethod
from enum import Enum
from typing import Literal

from PIL.Image import Image


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


class DoubleImageEffect(ImageEffect, ABC):
    @abstractmethod
    def apply(self, left: Image, right: Image) -> Image:
        pass


class ImageEffectError(Exception):
    pass
