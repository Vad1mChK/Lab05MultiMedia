import numpy as np
from PIL import Image
from typing import Dict, List, Callable

from src.image_editor.image_effects import SingleImageEffect, ImageEffectType, ImageEffectError


class ColorMatrixEffect(SingleImageEffect):
    """
    Applies a 4x5 color transformation matrix to an RGBA image. The matrix is interpreted as:
        | OutR | = | InR | x [ rR rG rB rA ] + | rO |
        | OutG | = | InR | x [ gR gG gB gA ] + | gO |
        | OutB | = | InR | x [ bR bG bB bA ] + | bO |
        | OutA | = | InR | x [ aR aG aB aA ] + | aO |

    where the 5th column (Offset) is in the 0..1 range and gets scaled by 255 at runtime.
    All channels are clipped to 0..255 at the end.
    """

    def __init__(self, matrix_4x5_callable: Callable[[], List[List[float]]]):
        """
        :param matrix_4x5: A 4x5 matrix (list of lists).
        :raises ImageEffectError: If the matrix dimensions are not 4 rows x 5 cols.
        """
        super().__init__(effect_type=ImageEffectType.COLOR_MATRIX)

        matrix_4x5 = matrix_4x5_callable()

        # Validate shape
        if len(matrix_4x5) != 4 or any(len(row) != 5 for row in matrix_4x5):
            raise ImageEffectError("ColorMatrixEffect requires a 4x5 matrix.")

        self.matrix = np.array(matrix_4x5, dtype=np.float32)

    def apply(self, image: Image) -> Image:
        """
        Applies the 4x5 matrix transformation to each pixel of the image.
        Converts the image to RGBA if not already.
        """
        # Convert image to RGBA so we have 4 channels
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        data = np.array(image, dtype=np.float32)  # Shape: (H, W, 4)

        # Separate coefficients (4x4) and offsets (4)
        coeffs = self.matrix[:, :4]  # shape: (4,4)
        offsets = self.matrix[:, 4]  # shape: (4,)

        # Scale offsets from 0..1 to 0..255
        offsets_scaled = offsets * 255.0

        # data shape: (H, W, 4)
        # we want result shape: (H, W, 4)
        # tensordot with axes=([2], [1]) => sum across channel dimension
        transformed = np.tensordot(data, coeffs, axes=([2], [1]))  # shape: (H, W, 4)
        transformed += offsets_scaled  # Broadcasting offsets to (H, W, 4)

        # Clip and convert back to uint8
        transformed = np.clip(transformed, 0, 255).astype(np.uint8)
        out_img = Image.fromarray(transformed, mode="RGBA")

        return out_img


#
# Some PRESETS
#

presets: dict[str, Callable[[], List[List[float]]]] = {
    'Identity': lambda: [
        [1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 1, 0],
    ],
    'Grayscale': lambda: [
        [0.299, 0.587, 0.114, 0, 0],
        [0.299, 0.587, 0.114, 0, 0],
        [0.299, 0.587, 0.114, 0, 0],
        [0,     0,     0,     1, 0],
    ],
    'Sepia': lambda: [
        [0.390, 0.769, 0.189, 0, 0],
        [0.349, 0.686, 0.168, 0, 0],
        [0.272, 0.534, 0.131, 0, 0],
        [0,     0,     0,     1, 0],
    ],
    'Green Sepia': lambda: [
        [0.272, 0.534, 0.131, 0, 0],
        [0.390, 0.769, 0.189, 0, 0],
        [0.349, 0.686, 0.168, 0, 0],
        [0,     0,     0,     1, 0],
    ],
    'RGB to BGR': lambda: [
        [0, 0, 1, 0, 0],
        [0, 1, 0, 0, 0],
        [1, 0, 0, 0, 0],
        [0, 0, 0, 1, 0],
    ],
    'Invert': lambda: [
        [-1, 0,  0,  0, 1],
        [0,  -1, 0,  0, 1],
        [0,  0,  -1, 0, 1],
        [0,  0,  0,  1, 0],
    ],
    'Silhouette': lambda: [
        [0, 0, 0, 1, 0],
        [0, 0, 0, 1, 0],
        [0, 0, 0, 1, 0],
        [0, 0, 0, 0, 1],
    ],
    'Isolate Red': lambda: [
        [1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0],
    ],
    'Isolate Green': lambda: [
        [0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0],
    ],
    'Isolate Blue': lambda: [
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 1, 0],
    ]
}


#
# Example usage:
#
if __name__ == "__main__":
    # Load an image
    test_img = Image.open("../../../examples/godot.png")
    for (preset_name, preset_value) in presets.items():
        test_result = ColorMatrixEffect(preset_value).apply(test_img)
        test_result.save(f"../../../examples/color_matrix/godot_{preset_name}.png")
