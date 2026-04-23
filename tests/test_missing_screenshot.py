"""
Regression test for the missing-screenshot path in gallery generation.

When `generate_tweet_screenshots()` fails on one card it logs a warning and
leaves that key absent from the screenshots dict. `generate_gallery_images()`
used to index the dict unconditionally, which turned a single Playwright hiccup
into a hard `KeyError` that aborted the entire run. This test locks in the
current behavior: one missing screenshot is skipped with a warning, remaining
cards are still generated.
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import generate_dril_tarot_images as gen


def _stub_mapping():
    return {
        'metadata': {'total_matches': 2},
        'cards': {
            'The Fool': {
                'upright': {
                    'tweet_content': 'hello',
                    'tweet_date': '2020-01-01 00:00:00',
                    'retweets': 1,
                    'favorites': 1,
                },
            },
            'The Magician': {
                'upright': {
                    'tweet_content': 'world',
                    'tweet_date': '2020-01-01 00:00:00',
                    'retweets': 1,
                    'favorites': 1,
                },
            },
        },
    }


def test_missing_screenshot_is_skipped_not_raised(tmp_path, capsys):
    mapping = _stub_mapping()
    cards_dir = tmp_path / 'cards'
    cards_dir.mkdir()
    output_dir = tmp_path / 'gallery'

    # Only create the image for The Magician; The Fool's card file isn't needed
    # because its screenshot is intentionally missing and should be skipped
    # before the card file is ever opened.
    magician_card = cards_dir / 'the-magician.jpg'
    Image.new('RGB', (400, 600), (255, 255, 255)).save(magician_card, 'JPEG')

    # screenshots dict is missing ('The Fool', 'upright') to simulate a failed
    # Playwright screenshot that was logged-and-continued earlier.
    screenshots = {
        ('The Magician', 'upright'): _png_bytes(),
    }

    with patch.object(gen, 'load_cached_screenshots', return_value=screenshots):
        gen.generate_gallery_images(
            mapping,
            str(cards_dir),
            str(output_dir),
            skip_existing=False,
            regenerate_screenshots=False,
        )

    # The Magician's image should be produced
    assert (output_dir / 'the-magician-upright.png').exists()
    # The Fool's image must NOT be produced (its screenshot was missing)
    assert not (output_dir / 'the-fool-upright.png').exists()

    # A warning mentioning the missing card + position should appear on stderr
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert 'The Fool' in combined
    assert 'upright' in combined.lower()


def _png_bytes():
    from io import BytesIO
    buf = BytesIO()
    Image.new('RGB', (200, 200), (200, 200, 200)).save(buf, 'PNG')
    return buf.getvalue()
