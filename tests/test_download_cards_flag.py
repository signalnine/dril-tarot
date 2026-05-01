"""
Regression test for the --download-cards flag.

The flag historically called download_rws_cards() which only printed manual
download instructions and prompted via input() -- it did NOT actually
download. Users hitting --download-cards expecting cards on disk got a wall
of text instead. This test pins the contract that --download-cards delegates
to the working downloader (download_tarot_cards.download_cards) without
prompting on stdin.
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import generate_dril_tarot_images as gen


def test_download_rws_cards_delegates_to_real_downloader(tmp_path):
    """download_rws_cards must call download_tarot_cards.download_cards,
    not block on stdin input()."""
    import download_tarot_cards

    output_dir = str(tmp_path / 'cards')

    with patch.object(download_tarot_cards, 'download_cards', return_value=True) as mock_dl, \
         patch('builtins.input', side_effect=AssertionError(
             'download_rws_cards must not prompt the user via input()')):
        result = gen.download_rws_cards(output_dir)

    assert result is True
    mock_dl.assert_called_once()
    # First positional arg (or 'output_dir' kwarg) should be the directory.
    args, kwargs = mock_dl.call_args
    passed_dir = kwargs.get('output_dir', args[0] if args else None)
    assert passed_dir == output_dir


def test_download_rws_cards_propagates_failure(tmp_path):
    """When the downloader reports failure, the wrapper must too."""
    import download_tarot_cards

    output_dir = str(tmp_path / 'cards')

    with patch.object(download_tarot_cards, 'download_cards', return_value=False):
        result = gen.download_rws_cards(output_dir)

    assert result is False
