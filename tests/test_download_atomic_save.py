"""
Regression test for dril-tarot-bga.

download_tarot_cards.download_cards used to call img.save(output_path) directly,
so a kill mid-write left a truncated JPG at the final path. The fix writes
to <output_path>.tmp and os.replaces; a save crash must leave the final path
unchanged (or absent on first download) and no tempfile behind.
"""

import os
import sys
from io import BytesIO

from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import download_tarot_cards


def _fake_png_response():
    buf = BytesIO()
    Image.new('RGB', (16, 16), (255, 0, 0)).save(buf, format='PNG')

    class _Resp:
        content = buf.getvalue()
        def raise_for_status(self):
            pass
    return _Resp()


def test_save_failure_leaves_no_partial_file(tmp_path, monkeypatch):
    cards_dir = tmp_path / 'tarot-cards'
    cards_dir.mkdir()

    monkeypatch.setattr(
        download_tarot_cards, 'CARD_URLS',
        {'The Fool': 'major_arcana_fool.png'},
    )
    monkeypatch.setattr(
        download_tarot_cards.requests, 'get',
        lambda url, headers=None, timeout=None: _fake_png_response(),
    )

    expected_path = cards_dir / (
        download_tarot_cards.sanitize_filename('The Fool') + '.jpg'
    )

    real_save = Image.Image.save

    def boom(self, fp, *args, **kwargs):
        # Simulate disk-full or SIGINT after some bytes have been written:
        # write a partial file to the tempfile path, then raise.
        if isinstance(fp, str):
            with open(fp, 'wb') as f:
                f.write(b'\xff\xd8\xff')  # JPEG SOI but truncated
        raise IOError("simulated kill mid-write")

    monkeypatch.setattr(Image.Image, 'save', boom)

    download_tarot_cards.download_cards(str(cards_dir))

    # Restore save so any later asserts that use it work.
    monkeypatch.setattr(Image.Image, 'save', real_save)

    assert not expected_path.exists(), (
        "atomic save: a failed download must NOT leave a partial JPG at the "
        "final path"
    )
    assert not (cards_dir / (expected_path.name + '.tmp')).exists(), (
        "tempfile must be cleaned up on save failure"
    )


def test_happy_path_writes_decodable_jpeg(tmp_path, monkeypatch):
    cards_dir = tmp_path / 'tarot-cards'
    cards_dir.mkdir()

    monkeypatch.setattr(
        download_tarot_cards, 'CARD_URLS',
        {'The Fool': 'major_arcana_fool.png'},
    )
    monkeypatch.setattr(
        download_tarot_cards.requests, 'get',
        lambda url, headers=None, timeout=None: _fake_png_response(),
    )

    ok = download_tarot_cards.download_cards(str(cards_dir))
    assert ok is True

    expected_path = cards_dir / (
        download_tarot_cards.sanitize_filename('The Fool') + '.jpg'
    )
    assert expected_path.exists()
    assert not (cards_dir / (expected_path.name + '.tmp')).exists(), (
        "no stray tempfile after a successful save"
    )
    with Image.open(expected_path) as img:
        img.verify()
    with Image.open(expected_path) as img:
        img.load()
