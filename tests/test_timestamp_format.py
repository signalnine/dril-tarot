"""
Regression test pinning timestamp generation in match_dril_tweets.

`datetime.utcnow()` is deprecated in Python 3.12 and slated for removal. The
two call sites that serialize `generated_at` (save_tweet_embeddings and
save_results) must switch to timezone-aware `datetime.now(timezone.utc)` while
keeping the trailing 'Z' ISO-8601 suffix that existing cached/emitted JSON
already uses -- downstream consumers may be parsing that format. This test
runs the save helpers with DeprecationWarning promoted to an error and checks
both: no deprecation fires, and the serialized timestamp still ends with 'Z'
(not '+00:00').
"""

import json
import os
import sys
import warnings

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import match_dril_tweets as mdt


def _load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_save_tweet_embeddings_is_deprecation_free_and_keeps_z_suffix(tmp_path):
    output = tmp_path / 'embeddings.json'
    with warnings.catch_warnings():
        warnings.simplefilter('error', DeprecationWarning)
        mdt.save_tweet_embeddings({'t1': [0.1, 0.2]}, [], str(output))

    data = _load(output)
    ts = data['generated_at']
    assert ts.endswith('Z'), (
        f"generated_at must keep trailing 'Z' for backward compatibility; got {ts!r}"
    )
    assert '+00:00' not in ts, (
        f"generated_at should not expose the raw '+00:00' offset; got {ts!r}"
    )


def test_save_results_is_deprecation_free_and_keeps_z_suffix(tmp_path):
    output = tmp_path / 'mapping.json'
    with warnings.catch_warnings():
        warnings.simplefilter('error', DeprecationWarning)
        mdt.save_results(
            {},
            str(output),
            system='modern_intuitive',
            min_retweets=50,
            popularity_weight=0.1,
        )

    data = _load(output)
    ts = data['metadata']['generated_at']
    assert ts.endswith('Z'), (
        f"metadata.generated_at must keep trailing 'Z'; got {ts!r}"
    )
    assert '+00:00' not in ts, (
        f"metadata.generated_at should not expose '+00:00'; got {ts!r}"
    )
