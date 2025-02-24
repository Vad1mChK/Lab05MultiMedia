from enum import Enum
import numpy as np
from PIL.Image import Image
import PIL.Image as ImageModule

from src.image_analyzer.image_effects import DoubleImageEffect, ImageEffectType


class BlendMode(Enum):
    NORMAL = 'Normal'
    LINEAR_DODGE = 'Linear Dodge'
    SCREEN = 'Screen'
    LINEAR_BURN = 'Linear Burn'
    MULTIPLY = 'Multiply'
    SUBTRACT = 'Subtract'
    DIFFERENCE = 'Difference'
    OVERLAY = 'Overlay'


_neutral_colors: dict[BlendMode, tuple] = {
    BlendMode.NORMAL: (255, 255, 255),
    BlendMode.LINEAR_DODGE: (0, 0, 0),
    BlendMode.SCREEN: (0, 0, 0),
    BlendMode.LINEAR_BURN: (255, 255, 255),
    BlendMode.MULTIPLY: (255, 255, 255),
    BlendMode.SUBTRACT: (0, 0, 0),
    BlendMode.DIFFERENCE: (0, 0, 0),
    BlendMode.OVERLAY: (128, 128, 128),
}


def blend(left: Image, right: Image, mode: BlendMode = BlendMode.NORMAL) -> Image:
    def __blend_helper(left_arr: np.ndarray,
                       right_arr: np.ndarray,
                       mask: np.ndarray) -> np.ndarray:
        _FACTOR = 255.0
        left_norm = left_arr.astype(np.float32) / _FACTOR
        right_norm = right_arr.astype(np.float32) / _FACTOR
        result_norm = np.zeros_like(left_norm)

        match mode:
            case BlendMode.NORMAL:
                result_norm = right_norm
            case BlendMode.LINEAR_DODGE:
                result_norm = left_norm + right_norm
            case BlendMode.SCREEN:
                result_norm = 1.0 - (1.0 - left_norm) * (1.0 - right_norm)
            case BlendMode.LINEAR_BURN:
                result_norm = left_norm + right_norm - 1.0
            case BlendMode.MULTIPLY:
                result_norm = left_norm * right_norm
            case BlendMode.SUBTRACT:
                result_norm = left_norm - right_norm
            case BlendMode.DIFFERENCE:
                result_norm = np.abs(left_norm - right_norm)
            case BlendMode.OVERLAY:
                result_norm = np.where(
                    left_norm <= 0.5,
                    2.0 * left_norm * right_norm,
                    1.0 - 2.0 * (1.0 - left_norm) * (1.0 - right_norm)
                )
            case _:
                result_norm = right_norm

        result_norm = np.clip(result_norm, 0.0, 1.0)
        blended_result = (result_norm * _FACTOR).astype(np.uint8)
        final_result = (mask[:, :, None] * blended_result +
                        (1.0 - mask)[:, :, None] * left_arr)
        return np.round(final_result).astype(np.uint8)

    def extract_alpha(image: Image) -> np.ndarray:
        _FACTOR = 255.0
        match image.mode:
            case 'RGBA':
                alpha_channel = np.array(image)[:, :, 3]
                return alpha_channel.astype(np.float32) / _FACTOR
            case _:
                return np.ones((image.height, image.width), dtype=np.float32)

    bounding_box_size = (
        max(left.width, right.width),
        max(left.height, right.height),
    )

    left_canvas = ImageModule.new('RGB', bounding_box_size)
    right_canvas = ImageModule.new(
        'RGB', bounding_box_size, color=_neutral_colors[mode])
    right_canvas_alpha = ImageModule.new(
        'RGBA', bounding_box_size, (0, 0, 0, 0))

    left_paste_position = (
        (bounding_box_size[0] - left.width) // 2,
        (bounding_box_size[1] - left.height) // 2
    )
    right_paste_position = (
        (bounding_box_size[0] - right.width) // 2,
        (bounding_box_size[1] - right.height) // 2
    )
    left_canvas.paste(left, left_paste_position)
    right_canvas.paste(right, right_paste_position)
    right_canvas_alpha.paste(right, right_paste_position)

    mask = extract_alpha(right_canvas_alpha)

    result = ImageModule.fromarray(
        __blend_helper(
            np.array(left_canvas),
            np.array(right_canvas),
            mask
        )
    )

    return result


class BlendImagesEffect(DoubleImageEffect):
    def __init__(self, blend_mode: BlendMode):
        super().__init__(effect_type=ImageEffectType.BLEND)
        self.blend_mode = blend_mode

    def apply(self, left: Image, right: Image) -> Image:
        return blend(left, right, blend_mode)


if __name__ == '__main__':
    left = ImageModule.open("../../../examples/china.jpg")
    right = ImageModule.open("../../../examples/backrooms.webp")
    result = blend(left, right, BlendMode.DIFFERENCE)
    result.show()

    for blend_mode in BlendMode:
        result = blend(left, right, blend_mode)
        result.save(f"../../../examples/blend/china_{blend_mode.name}.png")