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
    a: float


@dataclass
class HSLColor:
    h: float
    s: float
    l: float


@dataclass
class HSLAColor(HSLColor):
    a: float


def rgb_to_rgba(rgb: RGBColor) -> RGBAColor:
    return RGBAColor(rgb.r, rgb.g, rgb.b, 1.0)


def rgb_to_hsl(rgb: RGBColor) -> HSLColor:
    m_max = max(rgb.r, rgb.g, rgb.b)
    m_min = min(rgb.r, rgb.g, rgb.b)
    c = m_max - m_min

    h_mod = 0
    if c != 0:
        if m_max == rgb.r:
            h_mod = ((rgb.g - rgb.b) / c) % 6
        elif m_max == rgb.g:
            h_mod = ((rgb.b - rgb.r) / c) + 2
        elif m_max == rgb.b:
            h_mod = ((rgb.r - rgb.g) / c) + 4
    h = h_mod * 60

    l = (m_max + m_min) / 2

    s = 0
    if not (l == 1 or l == 0):
        s = c / (1 - abs(2 * l - 1))

    return HSLColor(h, s, l)



def rgba_to_rgb(rgba: RGBAColor) -> RGBColor:
    return RGBColor(rgba.r, rgba.g, rgba.b)


def channel_normalize(channel: float, scale: float = 255) -> float:
    return (channel / scale) if scale != 0 else 0


def channel_denormalize(channel: float, scale: float = 255) -> float:
    return channel * scale