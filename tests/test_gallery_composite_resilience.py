"""
Regression test for per-card composite resilience in gallery generation.

`generate_gallery_images()` already skips a card when its screenshot is missing
(see test_missing_screenshot.py). However, the composite + save step itself
had no per-card try/except, so a single PIL failure (corrupt card image,
unexpected mode, disk write error) on one of the 156 cards aborted the entire
run after the cached-screenshots phase had already succeeded -- wasting all
that setup time.

This test forces composite_tweet_on_card to raise for one specific card and
asserts the run continues to produce the remaining card.
"""

import os
import sys
from io import BytesIO
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import generate_dril_tarot_images as gen


def _png_bytes():
    buf = BytesIO()
    Image.new('RGB', (200, 200), (200, 200, 200)).save(buf, 'PNG')
    return buf.getvalue()


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


def test_composite_failure_on_one_card_does_not_abort_run(tmp_path, capsys):
    mapping = _stub_mapping()
    cards_dir = tmp_path / 'cards'
    cards_dir.mkdir()
    output_dir = tmp_path / 'gallery'

    # Both card images exist; the failure will be injected via composite mock.
    for slug in ('the-fool', 'the-magician'):
        Image.new('RGB', (400, 600), (255, 255, 255)).save(
            cards_dir / f'{slug}.jpg', 'JPEG'
        )

    screenshots = {
        ('The Fool', 'upright'): _png_bytes(),
        ('The Magician', 'upright'): _png_bytes(),
    }

    real_composite = gen.composite_tweet_on_card

    def flaky_composite(card_image_path, screenshot_bytes, card_name, position):
        if card_name == 'The Fool':
            raise OSError('simulated PIL failure on a corrupt card image')
        return real_composite(card_image_path, screenshot_bytes, card_name, position)

    with patch.object(gen, 'load_cached_screenshots', return_value=screenshots), \
         patch.object(gen, 'composite_tweet_on_card', side_effect=flaky_composite):
        gen.generate_gallery_images(
            mapping,
            str(cards_dir),
            str(output_dir),
            skip_existing=False,
            regenerate_screenshots=False,
        )

    # The Magician's image should still be produced despite The Fool failing.
    assert (output_dir / 'the-magician-upright.png').exists(), \
        "remaining cards must continue to be generated after a per-card failure"
    # The Fool's image must NOT exist (its composite raised).
    assert not (output_dir / 'the-fool-upright.png').exists()

    # Failure should be logged to stderr with the card identifier.
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert 'The Fool' in combined
    assert 'simulated PIL failure' in combined or 'failed' in combined.lower()


def test_save_failure_on_one_card_does_not_abort_run(tmp_path, capsys):
    """A PIL save error (e.g. disk full, encoder error) must not abort either."""
    mapping = _stub_mapping()
    cards_dir = tmp_path / 'cards'
    cards_dir.mkdir()
    output_dir = tmp_path / 'gallery'

    for slug in ('the-fool', 'the-magician'):
        Image.new('RGB', (400, 600), (255, 255, 255)).save(
            cards_dir / f'{slug}.jpg', 'JPEG'
        )

    screenshots = {
        ('The Fool', 'upright'): _png_bytes(),
        ('The Magician', 'upright'): _png_bytes(),
    }

    real_save = Image.Image.save
    fool_path_fragment = 'the-fool-upright.png'

    def flaky_save(self, fp, *args, **kwargs):
        if isinstance(fp, str) and fool_path_fragment in fp:
            raise OSError('simulated disk write failure')
        return real_save(self, fp, *args, **kwargs)

    with patch.object(gen, 'load_cached_screenshots', return_value=screenshots), \
         patch.object(Image.Image, 'save', flaky_save):
        gen.generate_gallery_images(
            mapping,
            str(cards_dir),
            str(output_dir),
            skip_existing=False,
            regenerate_screenshots=False,
        )

    assert (output_dir / 'the-magician-upright.png').exists()
    assert not (output_dir / 'the-fool-upright.png').exists()

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert 'The Fool' in combined
