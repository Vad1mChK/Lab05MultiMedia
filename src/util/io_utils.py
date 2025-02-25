import tempfile
from PIL.Image import Image

def save_temp_image(image: Image) -> str:
    temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    image.save(temp.name)
    temp.close()
    return temp.name
