"""
Regression test for dril-tarot-3fk.

match_tweets_to_cards previously called cosine_similarity in a Python loop
of ~1.4M iterations, each rewrapping the same ~1536-dim list as np.array.
This test pins that the vectorized rewrite produces the EXACT same matches
as a reference implementation using the per-pair scalar formulation, for
the same (system, min-retweets, popularity-weight) inputs and the same
tie-breaking (first eligible tweet wins on equal score).
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import match_dril_tweets as mdt


def _reference_match(
    cards,
    interpretations,
    card_embeddings,
    tweets,
    tweet_embeddings,
    system,
    min_retweets,
    popularity_weight,
):
    """Inline copy of the pre-vectorization loop for equivalence checking."""
    eligible_tweets = [t for t in tweets if t['retweets'] >= min_retweets]
    popularity_scores = mdt.calculate_popularity_scores(tweets)
    used_tweet_ids = set()
    matches = {}
    card_order = mdt.get_card_processing_order(cards)

    embedding_index = {}
    for emb_data in card_embeddings:
        key = (
            emb_data['card_name'],
            emb_data['position'],
            emb_data.get('interpretation_system', 'combined'),
        )
        embedding_index[key] = emb_data['embedding']

    for card_name in card_order:
        matches[card_name] = {}
        for position in ['upright', 'reversed']:
            card_embedding = embedding_index.get((card_name, position, system))
            if card_embedding is None:
                continue
            best_tweet = None
            best_score = -1.0
            best_similarity = 0.0
            v1 = np.array(card_embedding)
            n1 = np.linalg.norm(v1)
            for tweet in eligible_tweets:
                if tweet['id'] in used_tweet_ids:
                    continue
                if tweet['id'] not in tweet_embeddings:
                    continue
                v2 = np.array(tweet_embeddings[tweet['id']])
                n2 = np.linalg.norm(v2)
                similarity = 0.0 if n1 == 0 or n2 == 0 else float(np.dot(v1, v2) / (n1 * n2))
                popularity = popularity_scores.get(tweet['id'], 0.0)
                adjusted = similarity * (1 - popularity_weight) + popularity * popularity_weight
                if adjusted > best_score:
                    best_score = adjusted
                    best_similarity = similarity
                    best_tweet = tweet
            if best_tweet is None:
                continue
            used_tweet_ids.add(best_tweet['id'])
            matches[card_name][position] = {
                'tweet_id': best_tweet['id'],
                'similarity_score': float(best_similarity),
                'adjusted_score': float(best_score),
            }
    return matches


def _build_fixture(rng_seed: int = 0):
    rng = np.random.default_rng(rng_seed)
    # Small but structured: a few major arcana cards x both positions, with
    # 4-dim embeddings drawn from a uniform sphere.
    card_names = ['The Fool', 'The Magician', 'Strength', 'Death']
    cards = [{'name': n} for n in card_names]
    interpretations = {n: {} for n in card_names}

    def _normish(d):
        v = rng.standard_normal(d)
        return v.tolist()

    card_embeddings = []
    for n in card_names:
        for pos in ('upright', 'reversed'):
            card_embeddings.append({
                'card_name': n,
                'position': pos,
                'interpretation_system': 'modern_intuitive',
                'embedding': _normish(8),
            })

    tweets = []
    tweet_embeddings = {}
    for i in range(40):
        tid = f't{i}'
        tweets.append({
            'id': tid,
            'content': f'tweet {i} content',
            'date': '2020-01-01',
            'url': f'http://x/{i}',
            'retweets': 50 + i,
            'favorites': 100 + i,
        })
        tweet_embeddings[tid] = _normish(8)

    # A few tweets without embeddings -- they must be silently skipped.
    for i in range(40, 45):
        tid = f't{i}'
        tweets.append({
            'id': tid,
            'content': f'noemb {i}',
            'date': '2020-01-01',
            'url': f'http://x/{i}',
            'retweets': 60,
            'favorites': 100,
        })
    return cards, interpretations, card_embeddings, tweets, tweet_embeddings


def _shape(matches):
    """Project matches to the fields the vectorized impl is required to match."""
    out = {}
    for card_name, positions in matches.items():
        out[card_name] = {}
        for pos, entry in positions.items():
            out[card_name][pos] = {
                'tweet_id': entry['tweet_id'],
                'similarity_score': round(entry['similarity_score'], 10),
                'adjusted_score': round(entry['adjusted_score'], 10),
            }
    return out


def test_vectorized_matches_reference_on_synthetic_corpus(capsys):
    cards, interps, card_embs, tweets, tweet_embs = _build_fixture()

    expected = _reference_match(
        cards, interps, card_embs, tweets, tweet_embs,
        system='modern_intuitive', min_retweets=50, popularity_weight=0.1,
    )

    actual = mdt.match_tweets_to_cards(
        cards, interps, card_embs, tweets, tweet_embs,
        system='modern_intuitive', min_retweets=50, popularity_weight=0.1,
    )
    capsys.readouterr()  # discard progress prints

    assert _shape(actual) == _shape(expected)


def test_vectorized_handles_zero_popularity_weight(capsys):
    cards, interps, card_embs, tweets, tweet_embs = _build_fixture(rng_seed=1)
    expected = _reference_match(
        cards, interps, card_embs, tweets, tweet_embs,
        system='modern_intuitive', min_retweets=50, popularity_weight=0.0,
    )
    actual = mdt.match_tweets_to_cards(
        cards, interps, card_embs, tweets, tweet_embs,
        system='modern_intuitive', min_retweets=50, popularity_weight=0.0,
    )
    capsys.readouterr()
    assert _shape(actual) == _shape(expected)


def test_vectorized_skips_tweets_without_embedding(capsys):
    cards, interps, card_embs, tweets, tweet_embs = _build_fixture(rng_seed=2)
    matches = mdt.match_tweets_to_cards(
        cards, interps, card_embs, tweets, tweet_embs,
        system='modern_intuitive', min_retweets=50, popularity_weight=0.1,
    )
    capsys.readouterr()
    used_ids = {
        entry['tweet_id']
        for positions in matches.values()
        for entry in positions.values()
    }
    # Only tweets t0..t39 have embeddings.
    embedded = set(tweet_embs.keys())
    assert used_ids.issubset(embedded), (
        f"matched tweets {used_ids - embedded} have no embeddings"
    )
