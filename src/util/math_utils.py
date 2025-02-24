import numpy as np


def clamp(val, min_val, max_val):
    return max(min(val, max_val), min_val)


def clamp_01(val):
    return clamp(val, 0, 1)


def lerp(a, b, t):
    return a + (b - a) * t