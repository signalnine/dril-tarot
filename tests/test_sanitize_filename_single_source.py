"""
Regression test for dril-tarot-1zq.

sanitize_filename was previously defined identically in two places:
download_tarot_cards.sanitize_filename and
generate_dril_tarot_images.sanitize_filename. The two MUST agree because
the downloader writes <sanitize_filename(card)>.jpg and the gallery
generator/verifier reads it back. A divergence (e.g. different length cap
or unicode handling added to one but not the other) would silently break
verify_card_images on a complete card directory.

This test pins that there is exactly one definition and the gallery
generator delegates to the downloader's copy.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import download_tarot_cards
import generate_dril_tarot_images


def test_sanitize_filename_is_same_object():
    assert (
        generate_dril_tarot_images.sanitize_filename
        is download_tarot_cards.sanitize_filename
    ), (
        "generate_dril_tarot_images.sanitize_filename must be the same "
        "object as download_tarot_cards.sanitize_filename so a fix to one "
        "applies to both"
    )


def test_sanitize_filename_examples():
    """Pin the existing behavior so any future change is intentional."""
    sf = download_tarot_cards.sanitize_filename
    assert sf("The Fool") == "the-fool"
    assert sf("Ace of Wands") == "ace-of-wands"
    assert sf("Ten of Pentacles") == "ten-of-pentacles"
    # Path traversal is stripped
    assert ".." not in sf("../etc/passwd")
    # Null bytes are removed
    assert "\0" not in sf("foo\0bar")
    # Long names are truncated
    assert len(sf("x" * 1000)) <= 255
