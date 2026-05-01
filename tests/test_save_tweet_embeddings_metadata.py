"""
Regression test for save_tweet_embeddings metadata.

The 'tweets' parameter was previously unused, and the saved 'total_tweets'
field stored len(embeddings). When some batches fail in
generate_tweet_embeddings (it logs and continues), the result is fewer
embeddings than input tweets -- and the saved metadata silently mislabeled
the embedded count as the input count, hiding partial-failure incidents.

This test pins the corrected metadata: total_tweets reflects the input
tweet count, and a separate field tracks the embedded count.
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import match_dril_tweets


def test_save_tweet_embeddings_distinguishes_input_and_embedded_counts(tmp_path):
    tweets = [{'id': str(i), 'tweet_content': f'tweet {i}'} for i in range(10)]
    # Only 7 of the 10 succeeded -- the other 3 failed in a batch error.
    embeddings = {str(i): [0.1] * 1536 for i in range(7)}

    output_file = tmp_path / 'embeddings.json'
    match_dril_tweets.save_tweet_embeddings(embeddings, tweets, str(output_file))

    with open(output_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert data['total_tweets'] == len(tweets) == 10, \
        "total_tweets must reflect the INPUT tweet count, not embedded count"
    assert data['embedded_count'] == len(embeddings) == 7, \
        "embedded_count must reflect successfully embedded tweets"
    assert len(data['embeddings']) == 7
    assert data['model'] == 'text-embedding-3-small'
    assert data['dimension'] == 1536


def test_save_tweet_embeddings_full_success(tmp_path):
    """When every tweet embeds successfully, both counts agree."""
    tweets = [{'id': str(i), 'tweet_content': f'tweet {i}'} for i in range(5)]
    embeddings = {str(i): [0.1] * 1536 for i in range(5)}

    output_file = tmp_path / 'embeddings.json'
    match_dril_tweets.save_tweet_embeddings(embeddings, tweets, str(output_file))

    with open(output_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert data['total_tweets'] == 5
    assert data['embedded_count'] == 5
