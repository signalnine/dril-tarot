"""
Regression test for RGBA compositing in gallery generation.

`composite_tweet_on_card()` pastes a tweet screenshot (PNG, typically RGBA
because CSS border-radius produces transparent corners) onto an RGB card.
Without passing a mask, PIL drops the alpha channel, so transparent corner
pixels end up painted as solid RGB over the tarot card. This test builds a
tweet image with a clearly-marked transparent region and a clearly-marked
opaque region and asserts the card shows through the transparent region.
"""

import os
import sys
from io import BytesIO

from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import generate_dril_tarot_images as gen


CARD_COLOR = (180, 50, 40)        # distinctive card color (reddish)
TWEET_BODY_COLOR = (255, 255, 255) # white tweet body
TRANSPARENT_RGB = (7, 200, 13)     # distinctive RGB under alpha=0
                                   # (what PIL would paste if mask ignored)


def _rgba_tweet_png_bytes(size=(300, 200)) -> bytes:
    """Build an RGBA PNG where the left half is opaque white and the right
    half is fully transparent but with a recognizable RGB value. This mirrors
    the real failure mode: Playwright-rendered tweet screenshots have
    transparent pixels outside the border-radius whose RGB values depend on
    the renderer but are almost never the tarot card's color."""
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    w, h = size
    for y in range(h):
        for x in range(w):
            if x < w // 2:
                img.putpixel((x, y), (*TWEET_BODY_COLOR, 255))
            else:
                img.putpixel((x, y), (*TRANSPARENT_RGB, 0))
    buf = BytesIO()
    img.save(buf, 'PNG')
    return buf.getvalue()


def test_transparent_tweet_pixels_do_not_overwrite_card(tmp_path):
    # Save card as PNG (lossless) so we can assert exact pixel equality without
    # fighting JPEG quantization noise. composite_tweet_on_card auto-detects
    # the image format via PIL.Image.open.
    card_path = tmp_path / 'card.png'
    Image.new('RGB', (800, 1200), CARD_COLOR).save(card_path, 'PNG')

    tweet_bytes = _rgba_tweet_png_bytes(size=(300, 200))

    result = gen.composite_tweet_on_card(
        str(card_path),
        tweet_bytes,
        card_name='The Fool',
        position='upright',
    )

    assert result.mode == 'RGB'
    card_w, card_h = result.size

    # Tweet is centered. Compute pixel locations.
    # Tweet size is (300, 200), so x0 = (card_w - 300)//2, y0 = (card_h - 200)//2.
    x0 = (card_w - 300) // 2
    y0 = (card_h - 200) // 2

    # Left half of tweet is opaque white -> must appear white on result.
    opaque_px = result.getpixel((x0 + 50, y0 + 100))
    assert opaque_px == TWEET_BODY_COLOR, (
        f"opaque tweet pixel not preserved: got {opaque_px}, want {TWEET_BODY_COLOR}"
    )

    # Right half is transparent (alpha=0) -> card color must remain visible.
    transparent_px = result.getpixel((x0 + 250, y0 + 100))
    assert transparent_px == CARD_COLOR, (
        f"transparent tweet pixel overwrote the card: got {transparent_px}, "
        f"want card color {CARD_COLOR}"
    )


def test_opaque_rgb_tweet_still_composites(tmp_path):
    """Non-alpha tweet images must still paste correctly (no regression)."""
    card_path = tmp_path / 'card.png'
    Image.new('RGB', (800, 1200), CARD_COLOR).save(card_path, 'PNG')

    tweet = Image.new('RGB', (200, 100), (10, 20, 30))
    buf = BytesIO()
    tweet.save(buf, 'PNG')

    result = gen.composite_tweet_on_card(
        str(card_path),
        buf.getvalue(),
        card_name='The Fool',
        position='upright',
    )

    card_w, card_h = result.size
    x0 = (card_w - 200) // 2
    y0 = (card_h - 100) // 2

    # Center of tweet should match the tweet color.
    assert result.getpixel((x0 + 100, y0 + 50)) == (10, 20, 30)
