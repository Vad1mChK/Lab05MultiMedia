from enum import Enum
import numpy as np
import PIL.Image as ImageModule
from PIL.Image import Image

from src.image_editor.image_effects import ImageEffectError, SingleImageEffect, ImageEffectType


class GrayscaleAlgorithm(Enum):
    AVERAGE = 'Average'
    MAX = 'Max'
    MIN = 'Min'
    DESATURATE = 'Desaturate'
    PAL_NTSC = 'PAL or NTSC'
    HDTV = 'HDTV'
    HDR = 'HDR'
    ISOLATE_RED = 'Isolate Red'
    ISOLATE_GREEN = 'Isolate Green'
    ISOLATE_BLUE = 'Isolate Blue'
    GAMMA = 'Gamma Transform'


def grayscale(image: Image, algorithm: GrayscaleAlgorithm = GrayscaleAlgorithm.GAMMA) -> Image:
    img_array = np.array(image)
    if img_array.ndim == 2:
        return image.copy()

    has_alpha = img_array.shape[2] == 4
    rgb = img_array[..., :3]
    alpha = img_array[..., 3] if has_alpha else None

    def calculate_gray(rgb: np.ndarray) -> np.ndarray:
        match algorithm:
            case GrayscaleAlgorithm.AVERAGE:
                return np.mean(rgb, axis=2, dtype=np.float32)
            case GrayscaleAlgorithm.DESATURATE:
                max_val = np.max(rgb, axis=2).astype(np.float32)
                min_val = np.min(rgb, axis=2).astype(np.float32)
                return (max_val + min_val) / 2.0
            case GrayscaleAlgorithm.MAX:
                return np.max(rgb, axis=2).astype(np.float32)
            case GrayscaleAlgorithm.MIN:
                return np.min(rgb, axis=2).astype(np.float32)
            case GrayscaleAlgorithm.PAL_NTSC:
                coeffs = np.array([0.299, 0.587, 0.114], dtype=np.float32)
                return np.dot(rgb.astype(np.float32), coeffs)
            case GrayscaleAlgorithm.HDTV:
                coeffs = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
                return np.dot(rgb.astype(np.float32), coeffs)
            case GrayscaleAlgorithm.HDR:
                coeffs = np.array([0.2627, 0.6780, 0.0593], dtype=np.float32)
                return np.dot(rgb.astype(np.float32), coeffs)
            case GrayscaleAlgorithm.ISOLATE_RED:
                return rgb[..., 0].astype(np.float32)
            case GrayscaleAlgorithm.ISOLATE_GREEN:
                return rgb[..., 1].astype(np.float32)
            case GrayscaleAlgorithm.ISOLATE_BLUE:
                return rgb[..., 2].astype(np.float32)
            case GrayscaleAlgorithm.GAMMA:
                gamma_val = 2.4
                linear_rgb = (rgb.astype(np.float32) / 255.0) ** gamma_val
                coeffs = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
                linear_gray = np.dot(linear_rgb, coeffs)
                return (linear_gray ** (1.0 / gamma_val)) * 255.0
            case _:
                raise ImageEffectError(f"Unsupported algorithm: {algorithm}")

    gray = calculate_gray(rgb)
    gray = np.clip(gray, 0, 255).round().astype(np.uint8)
    new_rgb = np.stack([gray, gray, gray], axis=-1)

    if has_alpha:
        new_img_array = np.concatenate([new_rgb, alpha[..., np.newaxis]], axis=-1)
    else:
        new_img_array = new_rgb

    return ImageModule.fromarray(new_img_array)


class GrayscaleImageEffect(SingleImageEffect):
    def __init__(self, algorithm: GrayscaleAlgorithm = GrayscaleAlgorithm.GAMMA):
        super().__init__(effect_type=ImageEffectType.GRAYSCALE)
        self.algorithm = algorithm

    def apply(self, image: Image) -> Image:
        return grayscale(image, self.algorithm)


if __name__ == '__main__':
    img = ImageModule.open('../../../examples/china.jpg')
    img1 = grayscale(img, GrayscaleAlgorithm.GAMMA)
    img1.show()

    for algorithm in GrayscaleAlgorithm:
        img1 = grayscale(img, algorithm)
        img1.save(f"../../../examples/grayscale/china_{algorithm.name}.jpg")