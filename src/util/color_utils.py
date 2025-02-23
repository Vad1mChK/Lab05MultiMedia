import enum
from dataclasses import dataclass

from src.util.math_utils import clamp_01

class BlendMode(enum.Enum):
    ADD = 'ADD'
    SCREEN = 'SCREEN'
    MULTIPLY = 'MULTIPLY'
    BURN = 'BURN'
    OVERLAY = 'OVERLAY'
    DIFFERENCE = 'DIFFERENCE'


@dataclass
class RGBColor:
    r: float
    g: float
    b: float


@dataclass
class RGBAColor(RGBColor):
    a: float  # Alpha channel for transparency


def rgb_to_rgba(rgb: RGBColor) -> RGBAColor:
    return RGBAColor(rgb.r, rgb.g, rgb.b, 1.0)


def rgba_to_rgb(rgba: RGBAColor) -> RGBColor:
    return RGBColor(rgba.r, rgba.g, rgba.b)


def channel_normalize(channel: float, scale: float = 255) -> float:
    return (channel / scale) if scale != 0 else 0


def channel_denormalize(channel: float, scale: float = 255) -> float:
    return channel * scale


def rgb_to_grayscale(
        rgb: RGBColor,
        photoshop_mode: bool = False
) -> RGBColor:
    if photoshop_mode:
        return RGBColor(
            rgb.r * 0.299, rgb.g * 0.587, rgb.b * 0.114
        )
    else:
        gray = (rgb.r + rgb.g + rgb.b) / 3
        return RGBColor(gray, gray, gray)


def rgba_to_grayscale(
        rgba: RGBAColor,
        photoshop_mode: bool = False
) -> RGBAColor:
    rgb = rgba_to_rgb(rgba)
    rgb_gray = rgb_to_grayscale(rgb, photoshop_mode)
    rgba_gray = rgb_to_rgba(rgb_gray)
    rgba_gray.a = rgba.a
    return rgba_gray


def blend(
        left: RGBColor,
        right: RGBColor,
        blend_mode: BlendMode = BlendMode.ADD,
) -> RGBColor:
    return RGBColor(
        blend_channel(left.r, right.r, blend_mode),
        blend_channel(left.g, right.g, blend_mode),
        blend_channel(left.b, right.b, blend_mode),
    )


def blend_channel(left: float, right: float, blend_mode: BlendMode = BlendMode.ADD) -> float:
    l = channel_normalize(left)
    r = channel_normalize(right)

    result = l
    match blend_mode:
        case BlendMode.ADD:
            result = l + r
        case BlendMode.SCREEN:
            result = 1 - (1 - l) * (1 - r)
        case BlendMode.MULTIPLY:
            result = l * r
        case BlendMode.BURN:
            result = l + r - 1
        case BlendMode.OVERLAY:
            if left < 0.5:
                result = 2 * l * r
            else:
                result = 1 - 2 * (1 - l) * (1 - r)
        case BlendMode.DIFFERENCE:
            result = abs(l - r)
        case _:
            result = l  # Default to no change (if no match)

    result = clamp_01(result)
    return channel_denormalize(result)
