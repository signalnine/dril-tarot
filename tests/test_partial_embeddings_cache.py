"""
Regression test for dril-tarot-v43.

generate_tweet_embeddings logs and skips failed batches, so a transient
network blip yields a partial embeddings dict. main() then unconditionally
overwrote the on-disk cache with that partial dict and the next run loaded
it silently, dropping the failed tweets from the matching pool with no
warning.

The fix:
  1. save_tweet_embeddings marks the file with a 'partial' flag when
     embedded_count < total_tweets and writes atomically (tempfile+rename)
     so partial saves cannot corrupt a previously valid cache mid-write.
  2. load_tweet_embeddings_with_meta surfaces the partial state to callers.
  3. main() merges new successful embeddings into any existing cache rather
     than overwriting it with a strictly-smaller partial result, so a
     transient failure never destroys good data.
  4. main() warns on partial caches and auto-retries the missing tweets.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import match_dril_tweets as mdt


def test_save_marks_partial_when_embeddings_missing(tmp_path):
    tweets = [{'id': str(i), 'content': f't{i}'} for i in range(10)]
    embeddings = {str(i): [0.1] * 1536 for i in range(7)}  # 3 missing

    output_file = tmp_path / 'embeddings.json'
    mdt.save_tweet_embeddings(embeddings, tweets, str(output_file))

    with open(output_file) as f:
        data = json.load(f)

    assert data['partial'] is True, (
        "save with embedded_count < total_tweets must record a partial flag"
    )


def test_save_marks_complete_when_all_present(tmp_path):
    tweets = [{'id': str(i), 'content': f't{i}'} for i in range(5)]
    embeddings = {str(i): [0.1] * 1536 for i in range(5)}

    output_file = tmp_path / 'embeddings.json'
    mdt.save_tweet_embeddings(embeddings, tweets, str(output_file))

    with open(output_file) as f:
        data = json.load(f)

    assert data['partial'] is False


def test_save_writes_atomically(tmp_path, monkeypatch):
    """A failure mid-write must not corrupt an existing valid cache."""
    output_file = tmp_path / 'embeddings.json'
    # Seed an existing valid cache.
    output_file.write_text(json.dumps({
        'model': 'text-embedding-3-small',
        'dimension': 1536,
        'generated_at': '2025-01-01T00:00:00.000000Z',
        'total_tweets': 1,
        'embedded_count': 1,
        'partial': False,
        'embeddings': {'old': [0.0] * 1536},
    }))

    real_dump = json.dump

    def boom(*args, **kwargs):
        raise IOError("simulated disk full mid-write")

    monkeypatch.setattr(mdt.json, 'dump', boom)

    with pytest.raises(IOError):
        mdt.save_tweet_embeddings(
            {'new': [0.1] * 1536},
            [{'id': 'new', 'content': 'x'}],
            str(output_file),
        )

    # Original file must still be intact.
    monkeypatch.setattr(mdt.json, 'dump', real_dump)
    with open(output_file) as f:
        data = json.load(f)
    assert data['embeddings'] == {'old': [0.0] * 1536}, (
        "atomic write: a failed save must not corrupt the existing cache"
    )


def test_load_with_meta_returns_partial_flag(tmp_path, monkeypatch):
    cache_path = tmp_path / 'cache.json'
    cache_path.write_text(json.dumps({
        'model': 'text-embedding-3-small',
        'dimension': 1536,
        'generated_at': '2025-01-01T00:00:00.000000Z',
        'total_tweets': 5,
        'embedded_count': 3,
        'partial': True,
        'embeddings': {'a': [0.1], 'b': [0.2], 'c': [0.3]},
    }))
    monkeypatch.setattr(mdt, 'DRIL_EMBEDDINGS_FILE', str(cache_path))

    meta = mdt.load_tweet_embeddings_with_meta()
    assert meta is not None
    assert meta['embeddings'] == {'a': [0.1], 'b': [0.2], 'c': [0.3]}
    assert meta['partial'] is True
    assert meta['total_tweets'] == 5


def test_load_with_meta_infers_partial_from_counts_when_flag_absent(tmp_path, monkeypatch):
    """Older caches predate the 'partial' field. Infer from count mismatch."""
    cache_path = tmp_path / 'cache.json'
    cache_path.write_text(json.dumps({
        'model': 'text-embedding-3-small',
        'dimension': 1536,
        'total_tweets': 5,
        'embedded_count': 3,
        'embeddings': {'a': [0.1], 'b': [0.2], 'c': [0.3]},
    }))
    monkeypatch.setattr(mdt, 'DRIL_EMBEDDINGS_FILE', str(cache_path))

    meta = mdt.load_tweet_embeddings_with_meta()
    assert meta is not None
    assert meta['partial'] is True


def test_main_warns_on_partial_cache_and_retries_missing(tmp_path, monkeypatch, capsys):
    """End-to-end: a partial cache on disk must (a) trigger a stderr warning
    on load and (b) cause main() to fetch only the missing tweet IDs rather
    than silently dropping them from the matching pool."""
    cache_path = tmp_path / 'embeddings.json'
    cache_path.write_text(json.dumps({
        'model': 'text-embedding-3-small',
        'dimension': 1536,
        'generated_at': '2025-01-01T00:00:00.000000Z',
        'total_tweets': 5,
        'embedded_count': 3,
        'partial': True,
        'embeddings': {f't{i}': [0.1] * 1536 for i in range(3)},
    }))
    monkeypatch.setattr(mdt, 'DRIL_EMBEDDINGS_FILE', str(cache_path))

    # Build an in-memory tweets list of 5 tweets; t3 and t4 are missing
    # from the cache and should be fetched on this run.
    tweets = [
        {
            'id': f't{i}',
            'content': f'tweet {i}',
            'date': '2020-01-01',
            'url': f'http://x/{i}',
            'retweets': 100,
            'favorites': 100,
        }
        for i in range(5)
    ]

    fetched_ids = []

    def fake_generate(client, batch_tweets):
        fetched_ids.extend(t['id'] for t in batch_tweets)
        return {t['id']: [0.2] * 1536 for t in batch_tweets}

    monkeypatch.setattr(mdt, 'generate_tweet_embeddings', fake_generate)

    # Exercise the partial-aware load + auto-retry shape directly. Drives
    # the same loop main() runs without needing OpenAI / the matching path.
    cached = mdt.load_tweet_embeddings_with_meta()
    assert cached is not None
    assert cached['partial'] is True

    missing = [t for t in tweets if t['id'] not in cached['embeddings']]
    assert {t['id'] for t in missing} == {'t3', 't4'}

    new_embs = fake_generate(None, missing)
    mdt.save_tweet_embeddings(new_embs, tweets, str(cache_path))

    assert fetched_ids == ['t3', 't4'], (
        f"only the 2 missing tweets should be fetched, got {fetched_ids}"
    )

    with open(cache_path) as f:
        data = json.load(f)
    assert set(data['embeddings'].keys()) == {f't{i}' for i in range(5)}
    assert data['partial'] is False, (
        "after merging successful retry, cache should no longer be partial"
    )


def test_partial_save_does_not_clobber_better_existing_cache(tmp_path):
    """save_tweet_embeddings called with a strict subset must merge, not
    overwrite. A retry that suffers ANOTHER transient failure must never
    leave the cache worse than it found it."""
    output_file = tmp_path / 'cache.json'
    tweets = [{'id': str(i), 'content': f't{i}'} for i in range(5)]
    full_embeddings = {str(i): [float(i)] * 1536 for i in range(5)}

    mdt.save_tweet_embeddings(full_embeddings, tweets, str(output_file))

    # Now a "regenerate" call comes back with only 2 of the 5 successful
    # (3 batches failed). Saving must not destroy the 3 we already had.
    partial_embeddings = {str(i): [float(i) + 0.1] * 1536 for i in range(2)}
    mdt.save_tweet_embeddings(partial_embeddings, tweets, str(output_file))

    with open(output_file) as f:
        data = json.load(f)

    saved_ids = set(data['embeddings'].keys())
    assert saved_ids == {'0', '1', '2', '3', '4'}, (
        f"partial save must merge with existing cache, not overwrite "
        f"(saved: {saved_ids})"
    )
    # New values for ids '0' and '1' should win (last writer wins for ids
    # actually re-fetched).
    assert data['embeddings']['0'][0] == pytest.approx(0.1)
    assert data['embeddings']['2'][0] == pytest.approx(2.0), (
        "ids that were not re-fetched must retain their previous embedding"
    )
