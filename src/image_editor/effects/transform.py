from typing import Literal
import PIL.Image as ImageModule
from PIL.Image import Image, Transpose

from src.image_editor.image_effects import SingleImageEffect, ImageEffectType


def transform_image(
    image: Image,
    rotation: Literal[0, 90, 180, 270] = 0,
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
) -> Image:
    """
    Transforms the given image by rotating it (angle must be one of 0, 90, 180, 270)
    and optionally mirroring it.

    Args:
        image: A PIL Image instance.
        rotation: The rotation angle in degrees. Valid values are 0, 90, 180, or 270.
        flip_horizontal: Whether to flip the image horizontally.
        flip_vertical: Whether to flip the image vertically.

    Returns:
        The transformed PIL Image.
    """
    # Ensure the rotation angle is valid.
    if rotation not in (0, 90, 180, 270):
        raise ValueError("Rotation must be one of 0, 90, 180, or 270 degrees.")

    # Rotate using PIL's transpose constants.
    match rotation:
        case 90:
            image = image.transpose(Transpose.ROTATE_90)
        case 180:
            image = image.transpose(Transpose.ROTATE_180)
        case 270:
            image = image.transpose(Transpose.ROTATE_270)
        case _:
            pass
    # For rotation == 0, do nothing.

    # Apply mirroring if specified.
    if flip_horizontal:
        image = image.transpose(Transpose.FLIP_LEFT_RIGHT)
    if flip_vertical:
        image = image.transpose(Transpose.FLIP_TOP_BOTTOM)

    return image


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


if __name__ == "__main__":
    img = ImageModule.open("../../../examples/china.jpg")
    transformed_img = transform_image(img, rotation=90)
    transformed_img.show()
    transformed_img.save("../../../transformed_china.jpg")
