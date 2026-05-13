"""
Direct coverage for `composite_tweet_on_card` guard rails and the reversed
rotation branch. These paths were previously only exercised indirectly
via test_gallery_composite_resilience and test_transparent_composite, so
a regression in the guard-rail messages or rotation direction would not
have been caught.

Tracks bd issue dril-tarot-yk5.
"""

import os
import sys
from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import generate_dril_tarot_images as gen


def _tweet_png_bytes(size=(100, 60), color=(255, 255, 255)) -> bytes:
    img = Image.new('RGB', size, color)
    buf = BytesIO()
    img.save(buf, 'PNG')
    return buf.getvalue()


def test_zero_pixel_card_raises_value_error(tmp_path):
    """A zero-dimension card image must trigger the explicit dimension
    guard, not a downstream PIL error.

    PIL refuses to encode a 0-pixel image to PNG, so we can't save one on
    disk. Instead, patch Image.open to return an in-memory image whose
    width is 0; the function under test then hits the guard immediately.
    """
    # Path must exist so the path-only sanity (if any) succeeds; contents
    # are irrelevant since Image.open is patched.
    card_path = tmp_path / 'zero.png'
    Image.new('RGB', (1, 1)).save(card_path, 'PNG')

    zero_img = Image.new('RGB', (1, 1))
    # Force width to 0 via the underlying _size attribute. PIL's
    # Image.width is read from self.size, and Image.size returns
    # self._size, so this is the canonical way to fake a zero-pixel image
    # without convincing the PNG encoder to write one.
    zero_img._size = (0, 100)

    with patch.object(gen.Image, 'open', return_value=zero_img):
        with pytest.raises(ValueError, match='Invalid card image dimensions'):
            gen.composite_tweet_on_card(
                str(card_path),
                _tweet_png_bytes(),
                card_name='The Fool',
                position='upright',
            )


def test_oversize_card_raises_value_error(tmp_path):
    """A card larger than 10000 px on either axis must trigger the size
    guard before any resize / paste work happens."""
    card_path = tmp_path / 'huge.png'
    # 10001 x 10 is enough to trip the > 10000 check without allocating a
    # huge buffer.
    Image.new('RGB', (10001, 10), (10, 20, 30)).save(card_path, 'PNG')

    with pytest.raises(ValueError, match='Card image too large'):
        gen.composite_tweet_on_card(
            str(card_path),
            _tweet_png_bytes(),
            card_name='The Fool',
            position='upright',
        )


def test_reversed_position_rotates_card_180(tmp_path):
    """`position='reversed'` must rotate the card 180 degrees. We verify by
    painting a colored stripe across the TOP of the source card and asserting
    that, after rendering reversed, the stripe appears at the BOTTOM of the
    output instead of the top.

    The tweet screenshot is painted in the center, so we sample pixels in the
    margin columns (well away from x = card_width/2) to avoid the tweet
    overlay.
    """
    STRIPE_COLOR = (10, 200, 30)   # distinctive green
    BODY_COLOR = (180, 50, 40)     # distinctive red

    # Source card: red body with a green stripe across the top 50 rows.
    src_w, src_h = 800, 1200
    card = Image.new('RGB', (src_w, src_h), BODY_COLOR)
    for y in range(50):
        for x in range(src_w):
            card.putpixel((x, y), STRIPE_COLOR)
    card_path = tmp_path / 'striped.png'
    card.save(card_path, 'PNG')

    # Tweet small enough that the side margins of the output remain pure
    # card pixels at every row.
    tweet_bytes = _tweet_png_bytes(size=(200, 100), color=(255, 255, 255))

    upright = gen.composite_tweet_on_card(
        str(card_path), tweet_bytes,
        card_name='The Fool', position='upright',
    )
    reversed_ = gen.composite_tweet_on_card(
        str(card_path), tweet_bytes,
        card_name='The Fool', position='reversed',
    )

    # Both renderings must share the same output dimensions (the rotation
    # is 180 degrees, which preserves width and height).
    assert upright.size == reversed_.size, (
        f'upright/reversed sizes differ: {upright.size} vs {reversed_.size}'
    )
    out_w, out_h = upright.size

    # Sample column 10 (well inside the left margin, no tweet there) near
    # the top and bottom of each image.
    sample_x = 10
    near_top_y = 5
    near_bottom_y = out_h - 6

    # Upright: stripe near the top, body near the bottom.
    assert upright.getpixel((sample_x, near_top_y)) == STRIPE_COLOR, (
        'upright should have the green stripe near the top'
    )
    assert upright.getpixel((sample_x, near_bottom_y)) == BODY_COLOR, (
        'upright should have the red body near the bottom'
    )

    # Reversed: stripe is now at the bottom, body at the top.
    assert reversed_.getpixel((sample_x, near_top_y)) == BODY_COLOR, (
        'reversed should have the red body near the top'
    )
    assert reversed_.getpixel((sample_x, near_bottom_y)) == STRIPE_COLOR, (
        'reversed should have the green stripe near the bottom'
    )
