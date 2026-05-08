"""
Regression test for dril-tarot-41z.

The tweet-screenshot cache used to key by '<card>|<position>'. The key had
no relationship to which tweet was actually rendered, so changing the
matched tweet for a card (different --system, different --min-retweets,
or a manual edit to card_dril_mapping.json) silently kept serving the old
screenshot. The composite gallery would show the new mapping with stale
images and no warning.

The fix:
  1. cache_screenshots stores the tweet_id alongside the PNG bytes.
  2. load_cached_screenshots filters against the current mapping: any
     entry whose stored tweet_id does not match the mapping's current
     tweet_id is treated as stale and dropped.
  3. generate_gallery_images regenerates only the entries that are stale
     or missing -- a single mapping change does not reflow all 156 cards.
"""

import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import generate_dril_tarot_images as gen


def _mapping(tweet_ids):
    """Build a minimal mapping with the given (card, position) -> tweet_id assignments."""
    cards = {}
    for (card, position), tid in tweet_ids.items():
        cards.setdefault(card, {})[position] = {
            'tweet_id': tid,
            'tweet_content': f'content for {tid}',
            'tweet_date': '2020-01-01 00:00:00',
            'tweet_url': f'http://x/{tid}',
            'retweets': 100,
            'favorites': 100,
        }
    return {'metadata': {'total_matches': len(tweet_ids)}, 'cards': cards}


def test_cache_round_trip_preserves_screenshots(tmp_path, monkeypatch):
    """Sanity: cache/load round-trip with the new schema returns identical bytes."""
    cache_path = tmp_path / 'screenshots.json'
    monkeypatch.setattr(gen, 'TWEET_SCREENSHOTS_CACHE', str(cache_path))

    mapping = _mapping({
        ('The Fool', 'upright'): 'tweet-A',
        ('The Magician', 'upright'): 'tweet-B',
    })

    screenshots = {
        ('The Fool', 'upright'): b'\x89PNG-fool-bytes',
        ('The Magician', 'upright'): b'\x89PNG-mag-bytes',
    }
    gen.cache_screenshots(screenshots, mapping)

    loaded = gen.load_cached_screenshots(mapping)
    assert loaded == screenshots


def test_changed_tweet_id_invalidates_cache_entry(tmp_path, monkeypatch, capsys):
    cache_path = tmp_path / 'screenshots.json'
    monkeypatch.setattr(gen, 'TWEET_SCREENSHOTS_CACHE', str(cache_path))

    # Cache built from mapping A: Fool->tweet-A, Magician->tweet-B
    mapping_a = _mapping({
        ('The Fool', 'upright'): 'tweet-A',
        ('The Magician', 'upright'): 'tweet-B',
    })
    gen.cache_screenshots(
        {
            ('The Fool', 'upright'): b'screenshot-of-tweet-A',
            ('The Magician', 'upright'): b'screenshot-of-tweet-B',
        },
        mapping_a,
    )

    # Mapping B reassigns Magician to a different tweet. The Fool's
    # screenshot is still good; The Magician's is stale.
    mapping_b = _mapping({
        ('The Fool', 'upright'): 'tweet-A',
        ('The Magician', 'upright'): 'tweet-C',
    })

    loaded = gen.load_cached_screenshots(mapping_b)
    assert loaded == {('The Fool', 'upright'): b'screenshot-of-tweet-A'}, (
        "stale (Magician, upright) entry must be dropped; fresh entries kept"
    )


def test_only_stale_entries_are_regenerated(tmp_path, monkeypatch):
    """A single mapping change must not reflow all 156 screenshots."""
    cache_path = tmp_path / 'screenshots.json'
    monkeypatch.setattr(gen, 'TWEET_SCREENSHOTS_CACHE', str(cache_path))

    cards_dir = tmp_path / 'cards'
    cards_dir.mkdir()
    from PIL import Image
    for fname in ('the-fool.jpg', 'the-magician.jpg'):
        Image.new('RGB', (400, 600), (255, 255, 255)).save(cards_dir / fname, 'JPEG')
    output_dir = tmp_path / 'gallery'

    mapping_a = _mapping({
        ('The Fool', 'upright'): 'tweet-A',
        ('The Magician', 'upright'): 'tweet-B',
    })
    gen.cache_screenshots(
        {
            ('The Fool', 'upright'): _tiny_png(),
            ('The Magician', 'upright'): _tiny_png(),
        },
        mapping_a,
    )

    mapping_b = _mapping({
        ('The Fool', 'upright'): 'tweet-A',  # same tweet -> cache hit
        ('The Magician', 'upright'): 'tweet-C',  # changed -> regenerate
    })

    regenerated_calls = []

    def fake_generate(mapping_arg, only_for=None):
        # Only the missing/stale (card, position) pairs should be passed in.
        regenerated_calls.append(set(only_for) if only_for is not None else 'all')
        return {pair: _tiny_png() for pair in only_for}

    with patch.object(gen, 'generate_tweet_screenshots', side_effect=fake_generate):
        gen.generate_gallery_images(
            mapping_b,
            str(cards_dir),
            str(output_dir),
            skip_existing=False,
            regenerate_screenshots=False,
        )

    assert regenerated_calls == [{('The Magician', 'upright')}], (
        f"only the stale Magician entry should be regenerated; "
        f"got calls: {regenerated_calls}"
    )
    # And the gallery output for both cards should exist (Fool from cache,
    # Magician from regen).
    assert (output_dir / 'the-fool-upright.png').exists()
    assert (output_dir / 'the-magician-upright.png').exists()


def test_cache_without_tweet_ids_is_treated_as_stale(tmp_path, monkeypatch):
    """Older caches predate the tweet_id field; they cannot be validated
    and must be discarded rather than served as if fresh."""
    cache_path = tmp_path / 'screenshots.json'
    monkeypatch.setattr(gen, 'TWEET_SCREENSHOTS_CACHE', str(cache_path))

    # Write an old-format cache: { "card|pos": "<base64 png>" } with no
    # tweet_id sidecar.
    import base64
    old_format = {
        'The Fool|upright': base64.b64encode(b'old-format-bytes').decode('ascii'),
    }
    cache_path.write_text(json.dumps(old_format))

    mapping = _mapping({('The Fool', 'upright'): 'tweet-A'})

    loaded = gen.load_cached_screenshots(mapping)
    assert loaded == {}, (
        "old-format cache lacks tweet_ids and must not be served; "
        "callers will regenerate fresh entries"
    )


def _tiny_png():
    from io import BytesIO
    from PIL import Image
    buf = BytesIO()
    Image.new('RGB', (50, 50), (1, 2, 3)).save(buf, 'PNG')
    return buf.getvalue()
