"""
Regression test for dril-tarot-6st.

save_results previously wrote card_dril_mapping.json directly to the final
path; a crash mid-write left a truncated file that crashed the gallery
generator's load_card_mapping on the next run. The fix mirrors
save_tweet_embeddings: write to <output_file>.tmp then os.replace.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import match_dril_tweets as mdt


def _sample_matches():
    return {
        'The Fool': {
            'upright': {
                'tweet_id': '1',
                'tweet_content': 'x',
                'tweet_url': 'http://x/1',
                'tweet_date': '2020-01-01',
                'retweets': 100,
                'favorites': 200,
                'similarity_score': 0.5,
                'adjusted_score': 0.5,
                'card_interpretation': 'beginnings',
            }
        }
    }


def test_save_results_happy_path_leaves_no_tmp(tmp_path):
    output_file = tmp_path / 'card_dril_mapping.json'
    mdt.save_results(
        _sample_matches(), str(output_file),
        system='psychological', min_retweets=50, popularity_weight=0.1,
    )

    assert output_file.exists()
    assert not (tmp_path / 'card_dril_mapping.json.tmp').exists()

    with open(output_file) as f:
        data = json.load(f)
    assert data['cards']['The Fool']['upright']['tweet_id'] == '1'
    assert data['metadata']['interpretation_system'] == 'psychological'


def test_save_results_failure_preserves_existing_file(tmp_path, monkeypatch):
    """A crash mid-write must not corrupt a previously valid mapping file."""
    output_file = tmp_path / 'card_dril_mapping.json'
    # Seed an existing valid mapping.
    output_file.write_text(json.dumps({
        'metadata': {'interpretation_system': 'old'},
        'cards': {'Old Card': {}},
    }))

    real_dump = json.dump

    def boom(*args, **kwargs):
        raise IOError("simulated disk full mid-write")

    monkeypatch.setattr(mdt.json, 'dump', boom)

    with pytest.raises(IOError):
        mdt.save_results(
            _sample_matches(), str(output_file),
            system='psychological', min_retweets=50, popularity_weight=0.1,
        )

    # Original file must still be intact and parseable.
    monkeypatch.setattr(mdt.json, 'dump', real_dump)
    with open(output_file) as f:
        data = json.load(f)
    assert data['cards'] == {'Old Card': {}}, (
        "atomic write: a failed save_results must not corrupt the existing mapping"
    )
    # No stray tempfile.
    assert not (tmp_path / 'card_dril_mapping.json.tmp').exists()
