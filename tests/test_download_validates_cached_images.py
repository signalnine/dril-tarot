"""
Regression test for dril-tarot-4b2.

download_tarot_cards.download_cards used to short-circuit on
os.path.exists(output_path), regardless of whether the JPG was a zero-byte
file or a partially-written truncated image. A previous run killed
mid-Image.save() left the directory in exactly that state, and every
subsequent rerun reported the broken file as 'cached' with a green check.
Downstream PIL lazy loading would then surface the failure deep in the
gallery composite step.

The fix makes the cached-fast-path validate that the file is a complete,
decodable JPEG before counting it. Files that fail validation are deleted
so the download attempt actually happens.
"""

import os
import sys

import pytest
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import download_tarot_cards


def test_zero_byte_cached_file_is_deleted_and_redownload_attempted(tmp_path, monkeypatch):
    cards_dir = tmp_path / 'tarot-cards'
    cards_dir.mkdir()

    # Pretend the only card to download is The Fool, and seed a 0-byte JPG
    # at the path it would write to. The fast-path should NOT count this as
    # cached.
    monkeypatch.setattr(
        download_tarot_cards,
        'CARD_URLS',
        {'The Fool': 'major_arcana_fool.png'},
    )
    expected_path = cards_dir / (download_tarot_cards.sanitize_filename('The Fool') + '.jpg')
    expected_path.write_bytes(b'')
    assert expected_path.stat().st_size == 0

    download_attempted = {'count': 0}

    def fake_get(url, headers=None, timeout=None):
        download_attempted['count'] += 1
        # Return a tiny valid PNG so the conversion path succeeds.
        from io import BytesIO
        buf = BytesIO()
        Image.new('RGB', (8, 8), (255, 0, 0)).save(buf, format='PNG')

        class _Resp:
            content = buf.getvalue()
            def raise_for_status(self):
                pass
        return _Resp()

    monkeypatch.setattr(download_tarot_cards.requests, 'get', fake_get)

    ok = download_tarot_cards.download_cards(str(cards_dir))

    assert download_attempted['count'] == 1, (
        "zero-byte cached file should NOT be treated as a valid cache; "
        "the downloader must actually attempt the download"
    )
    assert ok is True
    # And the resulting file should be a real JPEG.
    assert expected_path.stat().st_size > 0
    with Image.open(expected_path) as img:
        img.verify()


def test_truncated_jpeg_cached_file_is_redownloaded(tmp_path, monkeypatch):
    cards_dir = tmp_path / 'tarot-cards'
    cards_dir.mkdir()

    monkeypatch.setattr(
        download_tarot_cards,
        'CARD_URLS',
        {'The Fool': 'major_arcana_fool.png'},
    )
    expected_path = cards_dir / (download_tarot_cards.sanitize_filename('The Fool') + '.jpg')

    # Build a real JPEG, then chop off the trailing bytes so PIL.verify()
    # rejects it. The exact truncation point doesn't matter; the file is
    # large enough to pass a naive size check but corrupt enough to fail
    # decoding.
    from io import BytesIO
    buf = BytesIO()
    Image.new('RGB', (200, 300), (50, 100, 200)).save(buf, format='JPEG', quality=95)
    full_bytes = buf.getvalue()
    expected_path.write_bytes(full_bytes[: len(full_bytes) // 2])

    download_attempted = {'count': 0}

    def fake_get(url, headers=None, timeout=None):
        download_attempted['count'] += 1
        out = BytesIO()
        Image.new('RGB', (200, 300), (50, 100, 200)).save(out, format='PNG')

        class _Resp:
            content = out.getvalue()
            def raise_for_status(self):
                pass
        return _Resp()

    monkeypatch.setattr(download_tarot_cards.requests, 'get', fake_get)

    ok = download_tarot_cards.download_cards(str(cards_dir))

    assert download_attempted['count'] == 1, (
        "truncated cached JPEG should fail validation and trigger a re-download"
    )
    assert ok is True
    # Final file must verify cleanly.
    with Image.open(expected_path) as img:
        img.verify()


def test_valid_cached_jpeg_is_kept_and_not_redownloaded(tmp_path, monkeypatch):
    cards_dir = tmp_path / 'tarot-cards'
    cards_dir.mkdir()

    monkeypatch.setattr(
        download_tarot_cards,
        'CARD_URLS',
        {'The Fool': 'major_arcana_fool.png'},
    )
    expected_path = cards_dir / (download_tarot_cards.sanitize_filename('The Fool') + '.jpg')
    Image.new('RGB', (300, 500), (10, 20, 30)).save(expected_path, format='JPEG', quality=95)
    original_size = expected_path.stat().st_size

    def fake_get(url, headers=None, timeout=None):
        raise AssertionError(
            "valid cached JPEG must short-circuit; downloader should not be called"
        )

    monkeypatch.setattr(download_tarot_cards.requests, 'get', fake_get)

    ok = download_tarot_cards.download_cards(str(cards_dir))

    assert ok is True
    assert expected_path.stat().st_size == original_size
