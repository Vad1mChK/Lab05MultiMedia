import matplotlib

matplotlib.use("QtAgg")  # Ensures compatibility with PySide6

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image


def display_color_distribution(pil_img: Image):
    """Displays a histogram of the color distribution of a PIL image."""

    img_array = np.array(pil_img)

    has_alpha = img_array.shape[-1] == 4 if len(img_array.shape) == 3 else False

    channels = ['Red', 'Green', 'Blue']
    colors = ['red', 'green', 'blue']

    if has_alpha:
        channels.append('Alpha')
        colors.append('gray')

    plt.figure(figsize=(10, 6))
    plt.title("Color Distribution")
    plt.xlabel("Pixel Intensity")
    plt.ylabel("Frequency")

    for i, (channel, color) in enumerate(zip(channels, colors)):
        channel_data = img_array[:, :, i].flatten() if len(img_array.shape) == 3 else img_array.flatten()
        plt.hist(channel_data, bins=256, alpha=0.5, color=color, label=channel)

    plt.legend()
    plt.show(block=False)


# Example usage:
if __name__ == '__main__':
    image_path = "../../examples/china.jpg"
    pil_img = Image.open(image_path)
    display_color_distribution(pil_img)
