"""
Regression test for corrupt tweet-embeddings cache handling.

`match_dril_tweets.load_tweet_embeddings` is the fallback loader for the
~370MB cache at `data/dril_tweet_embeddings.json`. A truncated write, a
partial download, or a JSON file missing the top-level `embeddings` key
used to raise `json.JSONDecodeError` / `KeyError` out of the helper and
abort the whole script from `main`'s catch-all handler. Users would see a
traceback and have no hint that the fix is "delete the cache and rerun".

The sibling `load_cached_screenshots` in `generate_dril_tarot_images.py`
already handles this case by warning and returning `None`; this file pins
the analogous behavior for `load_tweet_embeddings`, so a corrupt cache
degrades to "regenerate from scratch" instead of crashing.
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import match_dril_tweets as mdt


def test_missing_cache_returns_none(tmp_path, monkeypatch, capsys):
    cache_path = tmp_path / 'dril_tweet_embeddings.json'
    # Intentionally do not create the file.
    monkeypatch.setattr(mdt, 'DRIL_EMBEDDINGS_FILE', str(cache_path))

    result = mdt.load_tweet_embeddings()

    assert result is None
    captured = capsys.readouterr()
    assert captured.err == '', (
        f"missing-cache path should be silent; got stderr: {captured.err!r}"
    )


def test_invalid_json_returns_none_with_warning(tmp_path, monkeypatch, capsys):
    cache_path = tmp_path / 'dril_tweet_embeddings.json'
    cache_path.write_bytes(b'{not valid json at all')
    monkeypatch.setattr(mdt, 'DRIL_EMBEDDINGS_FILE', str(cache_path))

    result = mdt.load_tweet_embeddings()

    assert result is None, (
        "corrupt JSON should degrade to None so the caller regenerates"
    )
    captured = capsys.readouterr()
    assert captured.err != '', (
        "a corrupt cache should produce a stderr warning explaining the fallback"
    )


def test_missing_embeddings_key_returns_none_with_warning(tmp_path, monkeypatch, capsys):
    cache_path = tmp_path / 'dril_tweet_embeddings.json'
    # Valid JSON, but the expected shape is missing the 'embeddings' key.
    cache_path.write_text(json.dumps({'model': 'text-embedding-3-small'}))
    monkeypatch.setattr(mdt, 'DRIL_EMBEDDINGS_FILE', str(cache_path))

    result = mdt.load_tweet_embeddings()

    assert result is None
    captured = capsys.readouterr()
    assert captured.err != '', (
        "a cache missing the 'embeddings' key should warn before falling back"
    )


def test_valid_cache_roundtrips(tmp_path, monkeypatch, capsys):
    cache_path = tmp_path / 'dril_tweet_embeddings.json'
    payload = {
        'model': 'text-embedding-3-small',
        'dimension': 1536,
        'generated_at': '2025-01-01T00:00:00.000000Z',
        'total_tweets': 2,
        'embeddings': {
            't1': [0.1, 0.2, 0.3],
            't2': [0.4, 0.5, 0.6],
        },
    }
    cache_path.write_text(json.dumps(payload))
    monkeypatch.setattr(mdt, 'DRIL_EMBEDDINGS_FILE', str(cache_path))

    result = mdt.load_tweet_embeddings()

    assert result == payload['embeddings']
    captured = capsys.readouterr()
    assert captured.err == '', (
        f"happy path must not emit warnings; got stderr: {captured.err!r}"
    )
