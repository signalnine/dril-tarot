"""
Regression test for image_to_base64 handling of palette-mode PNGs.

`utils/download_dril_avatar.py::image_to_base64` flattens RGBA/LA inputs onto a
white background but falls through to a bare `Image.convert('RGB')` for every
other mode. Palette-mode (`P`) PNGs that encode transparency via the
`transparency` info key are silently painted with whatever palette color sits
at the transparent index instead of compositing onto white. This test pins
the intended behavior: transparent palette pixels must appear white in the
encoded avatar.

Assertions sample pixels from the center of uniformly-colored regions so that
JPEG's block-based DCT cannot bleed neighboring colors into the tested pixel.
"""

import base64
import os
import sys
from io import BytesIO

from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.download_dril_avatar import image_to_base64


TRANSPARENT_PALETTE_RGB = (0, 255, 0)  # value painted by the buggy path
OPAQUE_PALETTE_RGB = (255, 0, 0)


def _decode_avatar(data_uri: str) -> Image.Image:
    assert data_uri.startswith('data:image/jpeg;base64,'), data_uri[:40]
    jpg_bytes = base64.b64decode(data_uri.split(',', 1)[1])
    return Image.open(BytesIO(jpg_bytes)).convert('RGB')


def _make_p_mode_png(path, transparent_rect, size=(48, 48)):
    """Write a palette PNG. Pixels inside `transparent_rect` (left, top, right,
    bottom) use palette index 1, declared transparent via the PNG
    `transparency` key. All other pixels use palette index 0 (opaque red)."""
    palette = list(OPAQUE_PALETTE_RGB) + list(TRANSPARENT_PALETTE_RGB) + [0] * (256 * 3 - 6)
    img = Image.new('P', size, 0)
    img.putpalette(palette)
    left, top, right, bottom = transparent_rect
    for y in range(top, bottom):
        for x in range(left, right):
            img.putpixel((x, y), 1)
    img.save(path, 'PNG', transparency=1)


def test_p_mode_transparent_region_becomes_white(tmp_path):
    # Left half transparent, right half opaque red. Sampling the center of
    # each half keeps us well clear of the color boundary.
    src = tmp_path / 'avatar.png'
    _make_p_mode_png(src, transparent_rect=(0, 0, 24, 48))

    decoded = _decode_avatar(image_to_base64(str(src)))

    r, g, b = decoded.getpixel((12, 24))
    assert r > 230 and g > 230 and b > 230, (
        f"transparent P-mode region did not composite onto white background: "
        f"got ({r}, {g}, {b}) -- expected near-white. Palette color at the "
        f"transparent index was {TRANSPARENT_PALETTE_RGB}."
    )


def test_p_mode_opaque_region_is_preserved(tmp_path):
    src = tmp_path / 'avatar.png'
    _make_p_mode_png(src, transparent_rect=(0, 0, 24, 48))

    decoded = _decode_avatar(image_to_base64(str(src)))

    r, g, b = decoded.getpixel((36, 24))
    assert r > 200 and g < 60 and b < 60, (
        f"opaque palette pixel was not preserved: got ({r}, {g}, {b})"
    )


def test_rgba_transparent_region_still_flattens_onto_white(tmp_path):
    """Pre-existing RGBA path must not regress."""
    src = tmp_path / 'avatar.png'
    img = Image.new('RGBA', (48, 48), (255, 0, 0, 255))
    for y in range(48):
        for x in range(24):
            img.putpixel((x, y), (0, 255, 0, 0))
    img.save(src, 'PNG')

    decoded = _decode_avatar(image_to_base64(str(src)))

    r, g, b = decoded.getpixel((12, 24))
    assert r > 230 and g > 230 and b > 230, (
        f"RGBA transparent region regressed: got ({r}, {g}, {b})"
    )
