from abc import ABC, abstractmethod
from typing import List
from PIL import Image

# These imports assume that you have the following classes in your module:
# - ImageEffect, SingleImageEffect, DoubleImageEffect, and ImageEffectError
from src.image_editor.image_effects import (
    ImageEffect,
    SingleImageEffect,
    DoubleImageEffect,
    ImageEffectError
)

class ImageEffectApplier(ABC):
    def __init__(self):
        self.effects: List[ImageEffect] = []

    def __iadd__(self, effect: ImageEffect):
        self.effects.append(effect)
        return self

    def __isub__(self, effect: ImageEffect):
        self.effects.remove(effect)
        return self

    @abstractmethod
    def apply_all_effects(self) -> Image:
        pass

# SingleImageEditor that works only with SingleImageEffect.
class SingleImageEffectApplier(ImageEffectApplier):
    def __init__(self, original: Image):
        super().__init__()
        self.original_image = original
        # We narrow the type of effects list to only single-image effects.
        self.effects: List[SingleImageEffect] = []

    def __iadd__(self, effect: SingleImageEffect):
        if not isinstance(effect, SingleImageEffect):
            raise ImageEffectError("Effect must be an instance of SingleImageEffect")
        self.effects.append(effect)
        return self

    def __isub__(self, effect: SingleImageEffect):
        if effect in self.effects:
            self.effects.remove(effect)
        return self

    def apply_all_effects(self) -> Image:
        # Start with a copy of the original image.
        img = self.original_image.copy()
        for effect in self.effects:
            img = effect.apply(img)
        return img

# DoubleImageEditor that works only with DoubleImageEffect.
class DoubleImageEffectApplier(ImageEffectApplier):
    def __init__(self, left: Image, right: Image):
        super().__init__()
        self.left_image = left
        self.right_image = right
        # We narrow the effects list to only double-image effects.
        self.effects: List[DoubleImageEffect] = []

    def __iadd__(self, effect: DoubleImageEffect):
        if not isinstance(effect, DoubleImageEffect):
            raise ImageEffectError("Effect must be an instance of DoubleImageEffect")
        self.effects.append(effect)
        return self

    def __isub__(self, effect: DoubleImageEffect):
        if effect in self.effects:
            self.effects.remove(effect)
        return self

    def apply_all_effects(self) -> Image:
        # For double-image effects, you might define the semantics differently.
        # Here we assume that we start with the left image and apply each effect
        # in order, passing the right image as the second operand.
        img = self.left_image.copy()
        for effect in self.effects:
            # If the effect needs to combine the current image with the right image:
            img = effect.apply(img, self.right_image.copy())
        return img
