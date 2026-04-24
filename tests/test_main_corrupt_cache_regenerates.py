"""
Regression test: main() must regenerate embeddings when the cache load
returns None (corrupt or unreadable cache).

Commit 270ef6f made `load_tweet_embeddings` return None on corrupt cache
input so the script could degrade to regenerating from OpenAI rather than
abort. The caller in `main()` did not handle the None return -- it called
`len(None)` immediately after loading, which raised TypeError and bubbled
out through `main()`'s catch-all, undoing the entire benefit of the
graceful fallback. This test pins the contract: if the cache is present
but unreadable, `main()` regenerates and continues.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import match_dril_tweets as mdt


@pytest.fixture
def stub_environment(tmp_path, monkeypatch):
    """Point all I/O at tmp_path and stub network/data dependencies."""
    # Corrupt cache file -- valid JSON but missing 'embeddings' triggers
    # load_tweet_embeddings to return None with a warning.
    cache_path = tmp_path / 'dril_tweet_embeddings.json'
    cache_path.write_text(json.dumps({'model': 'text-embedding-3-small'}))
    monkeypatch.setattr(mdt, 'DRIL_EMBEDDINGS_FILE', str(cache_path))

    # Stub data loaders so we don't need real fixture files.
    monkeypatch.setattr(mdt, 'load_api_key', lambda: 'sk-test')
    monkeypatch.setattr(mdt, 'OpenAI', lambda api_key=None: object())
    monkeypatch.setattr(mdt, 'load_cards', lambda: [{'name': 'The Fool'}])
    monkeypatch.setattr(mdt, 'load_interpretations', lambda: {})
    monkeypatch.setattr(mdt, 'load_card_embeddings', lambda: [])
    monkeypatch.setattr(mdt, 'load_dril_tweets', lambda: [])

    # Track whether the regen path was hit.
    calls = {'generate': 0, 'save': 0}

    def fake_generate(client, tweets):
        calls['generate'] += 1
        return {'t1': [0.0]}

    def fake_save(embeddings, tweets, output_file):
        calls['save'] += 1

    monkeypatch.setattr(mdt, 'generate_tweet_embeddings', fake_generate)
    monkeypatch.setattr(mdt, 'save_tweet_embeddings', fake_save)

    # match_tweets_to_cards / save_results aren't relevant; stub them
    # so main() exits the happy path cleanly after the cache branch.
    monkeypatch.setattr(mdt, 'match_tweets_to_cards',
                        lambda *a, **kw: {})
    monkeypatch.setattr(mdt, 'save_results',
                        lambda matches, output_file, system, min_retweets, popularity_weight: None)

    # Run with no extra CLI args -- we only care about the cache branch.
    monkeypatch.setattr(sys, 'argv', ['match_dril_tweets.py',
                                       '--output', str(tmp_path / 'out.json')])

    return calls


def test_main_regenerates_when_cache_returns_none(stub_environment):
    """A corrupt cache must trigger regeneration, not crash main()."""
    calls = stub_environment

    # main() should complete without raising. On unfixed code this raises
    # TypeError("object of type 'NoneType' has no len()") which the
    # catch-all converts into SystemExit(1).
    mdt.main()

    assert calls['generate'] == 1, (
        "main() must call generate_tweet_embeddings when the cache load "
        "returns None"
    )
    assert calls['save'] == 1, (
        "main() must persist the regenerated embeddings via "
        "save_tweet_embeddings so the next run has a valid cache"
    )
