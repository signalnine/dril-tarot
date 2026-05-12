"""
Regression test for dril-tarot-cfo.

verify_card_images previously only checked os.path.exists, so a zero-byte
or truncated card JPG was reported as present. The fix routes the check
through download_tarot_cards.is_valid_cached_jpeg, matching the protection
dril-tarot-4b2 added on the writer side.
"""

import json
import os
import sys

import pytest
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import generate_dril_tarot_images as g
from download_tarot_cards import sanitize_filename


def _seed_mapping(tmp_path, card_names):
    mapping_path = tmp_path / 'card_dril_mapping.json'
    mapping_path.write_text(json.dumps({
        'metadata': {'interpretation_system': 'psychological'},
        'cards': {name: {} for name in card_names},
    }))
    return mapping_path


def test_zero_byte_card_is_reported_missing(tmp_path, monkeypatch):
    cards_dir = tmp_path / 'tarot-cards'
    cards_dir.mkdir()
    (cards_dir / (sanitize_filename('The Fool') + '.jpg')).write_bytes(b'')

    mapping_path = _seed_mapping(tmp_path, ['The Fool'])
    monkeypatch.setattr(g, 'CARD_MAPPING_FILE', str(mapping_path))

    ok, missing = g.verify_card_images(str(cards_dir))

    assert ok is False
    assert missing == ['The Fool'], (
        "zero-byte cached JPG must be reported as missing so the user "
        "knows to rerun --download-cards"
    )


def test_truncated_card_is_reported_missing(tmp_path, monkeypatch):
    cards_dir = tmp_path / 'tarot-cards'
    cards_dir.mkdir()

    from io import BytesIO
    buf = BytesIO()
    Image.new('RGB', (200, 300), (50, 100, 200)).save(buf, format='JPEG', quality=95)
    full_bytes = buf.getvalue()
    (cards_dir / (sanitize_filename('The Fool') + '.jpg')).write_bytes(
        full_bytes[: len(full_bytes) // 2]
    )

    mapping_path = _seed_mapping(tmp_path, ['The Fool'])
    monkeypatch.setattr(g, 'CARD_MAPPING_FILE', str(mapping_path))

    ok, missing = g.verify_card_images(str(cards_dir))

    assert ok is False
    assert missing == ['The Fool']


def test_valid_card_passes_verification(tmp_path, monkeypatch):
    cards_dir = tmp_path / 'tarot-cards'
    cards_dir.mkdir()
    Image.new('RGB', (300, 500), (10, 20, 30)).save(
        cards_dir / (sanitize_filename('The Fool') + '.jpg'),
        format='JPEG', quality=95,
    )

    mapping_path = _seed_mapping(tmp_path, ['The Fool'])
    monkeypatch.setattr(g, 'CARD_MAPPING_FILE', str(mapping_path))

    ok, missing = g.verify_card_images(str(cards_dir))

    assert ok is True
    assert missing == []
