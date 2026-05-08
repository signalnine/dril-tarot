#!/usr/bin/env python3
"""
Match dril tweets to tarot cards using semantic similarity.

This script generates embeddings for dril tweets and matches them to tarot cards
based on semantic similarity, with configurable popularity weighting and strict
uniqueness constraints.

Usage:
    # Generate matching with defaults
    python3 match_dril_tweets.py

    # Use specific interpretation system
    python3 match_dril_tweets.py --system jungian_psychological

    # Adjust popularity weighting
    python3 match_dril_tweets.py --min-retweets 100 --popularity-weight 0.2

    # Force regenerate tweet embeddings
    python3 match_dril_tweets.py --regenerate-embeddings
"""

import json
import os
import sys
import csv
import argparse
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timezone
from openai import OpenAI

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


# Configuration
CARDS_FILE = 'semantic-tarot/cards.json'
INTERPRETATIONS_FILE = 'semantic-tarot/interpretations.json'
CARD_EMBEDDINGS_FILE = 'semantic-tarot/card_embeddings.json'
DRIL_TWEETS_CSV = 'data/driltweets.csv'
DRIL_EMBEDDINGS_FILE = 'data/dril_tweet_embeddings.json'
DEFAULT_OUTPUT_FILE = 'data/card_dril_mapping.json'

# Card processing order (from tarot.py)
MAJOR_ARCANA = [
    "The Fool", "The Magician", "The High Priestess", "The Empress",
    "The Emperor", "The Hierophant", "The Lovers", "The Chariot",
    "Strength", "The Hermit", "Wheel of Fortune", "Justice",
    "The Hanged Man", "Death", "Temperance", "The Devil",
    "The Tower", "The Star", "The Moon", "The Sun",
    "Judgement", "The World"
]

SUITS = ['Wands', 'Cups', 'Swords', 'Pentacles']
RANKS = ['Ace', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
         'Eight', 'Nine', 'Ten', 'Page', 'Knight', 'Queen', 'King']


def load_api_key() -> str:
    """
    Load OpenAI API key from environment or ~/.env file.

    Returns:
        API key string

    Raises:
        ValueError: If API key not found
    """
    # Try environment variable first
    api_key = os.getenv('OPENAI_API_KEY')

    # Fall back to ~/.env file
    if not api_key and DOTENV_AVAILABLE:
        env_path = os.path.expanduser('~/.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)
            api_key = os.getenv('OPENAI_API_KEY')

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment or ~/.env file.\n"
            "Please set it with: export OPENAI_API_KEY='your-key-here'\n"
            "Or add it to ~/.env file: OPENAI_API_KEY=your-key-here"
        )

    return api_key


def load_cards() -> List[Dict]:
    """Load card data"""
    try:
        with open(CARDS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {CARDS_FILE}: {e}")


def load_interpretations() -> Dict:
    """Load interpretation data"""
    try:
        with open(INTERPRETATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {INTERPRETATIONS_FILE}: {e}")


def load_card_embeddings() -> List[Dict]:
    """Load pre-generated card embeddings"""
    if not os.path.exists(CARD_EMBEDDINGS_FILE):
        raise FileNotFoundError(
            f"Card embeddings file not found: {CARD_EMBEDDINGS_FILE}\n"
            "Please run generate_embeddings.py first to create embeddings."
        )

    try:
        with open(CARD_EMBEDDINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {CARD_EMBEDDINGS_FILE}: {e}")


def load_dril_tweets() -> List[Dict]:
    """
    Load dril tweets from CSV file.

    Returns:
        List of tweet dictionaries with id, content, date, retweets, favorites
    """
    tweets = []

    with open(DRIL_TWEETS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                # Parse retweets and favorites with error handling
                try:
                    retweets = int(row['retweets']) if row['retweets'] else 0
                except ValueError:
                    print(f"Warning: Invalid retweets value for tweet {row.get('id')}: {row.get('retweets')}", file=sys.stderr)
                    retweets = 0

                try:
                    favorites = int(row['favorites']) if row['favorites'] else 0
                except ValueError:
                    print(f"Warning: Invalid favorites value for tweet {row.get('id')}: {row.get('favorites')}", file=sys.stderr)
                    favorites = 0

                tweet = {
                    'id': row['id'],
                    'content': row['content'],
                    'date': row['date'],
                    'url': row['link'],
                    'retweets': retweets,
                    'favorites': favorites,
                }
                tweets.append(tweet)
            except KeyError as e:
                print(f"Warning: Skipping tweet row missing field: {e}", file=sys.stderr)
                continue

    return tweets


def generate_tweet_embeddings(client: OpenAI, tweets: List[Dict]) -> Dict[str, List[float]]:
    """
    Generate embeddings for all dril tweets.

    Args:
        client: OpenAI client instance
        tweets: List of tweet dictionaries

    Returns:
        Dictionary mapping tweet_id -> embedding vector
    """
    print(f"\nGenerating embeddings for {len(tweets)} tweets...")
    print("(This may take a minute)")

    embeddings = {}
    batch_size = 100
    failed_batches = []

    for i in range(0, len(tweets), batch_size):
        batch = tweets[i:i + batch_size]
        batch_end = min(i + batch_size, len(tweets))

        print(f"  Processing tweets {i+1}-{batch_end}...")

        # Prepare batch texts
        texts = [tweet['content'] for tweet in batch]
        tweet_ids = [tweet['id'] for tweet in batch]

        try:
            # Batch embed
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )

            # Store embeddings
            for tweet_id, embedding_data in zip(tweet_ids, response.data):
                embeddings[tweet_id] = embedding_data.embedding

        except Exception as e:
            print(f"  ✗ Error generating embeddings for batch: {e}", file=sys.stderr)
            failed_batches.append((i+1, batch_end, str(e)))
            # Continue with remaining batches

    if failed_batches:
        print(f"\n⚠ Warning: {len(failed_batches)} batch(es) failed:", file=sys.stderr)
        for start, end, error in failed_batches[:5]:
            print(f"  - Tweets {start}-{end}: {error}", file=sys.stderr)
        if len(failed_batches) > 5:
            print(f"  ... and {len(failed_batches) - 5} more", file=sys.stderr)

    print(f"✓ Generated {len(embeddings)} tweet embeddings")
    return embeddings


def save_tweet_embeddings(embeddings: Dict[str, List[float]], tweets: List[Dict], output_file: str) -> None:
    """Save tweet embeddings to cache file.

    total_tweets reflects the INPUT tweet count; embedded_count reflects how
    many actually got embeddings. They differ when some batches in
    generate_tweet_embeddings fail and are logged-and-skipped -- without a
    distinct input count, partial failures are invisible after the fact.

    Two extra protections against partial-failure-poisoning the cache:
      1. Merge against any existing on-disk cache so a retry that suffers
         a fresh transient failure never leaves the cache strictly worse
         than it found it.
      2. Write atomically via tempfile + os.replace so a crash mid-write
         cannot truncate the previous valid cache.
    """
    # Merge with existing cache: keep all prior embeddings, then layer the
    # newly-fetched ones on top. The new dict wins on key collisions, which
    # matches the user's intent when they pass --regenerate-embeddings.
    merged: Dict[str, List[float]] = {}
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            existing_emb = existing.get('embeddings')
            if isinstance(existing_emb, dict):
                merged.update(existing_emb)
        except (json.JSONDecodeError, OSError) as e:
            print(
                f"Warning: existing cache at {output_file} unreadable "
                f"({e}); proceeding with fresh save",
                file=sys.stderr,
            )
    merged.update(embeddings)

    is_partial = len(merged) < len(tweets)
    data = {
        'model': 'text-embedding-3-small',
        'dimension': 1536,
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z'),
        'total_tweets': len(tweets),
        'embedded_count': len(merged),
        'partial': is_partial,
        'embeddings': merged,
    }

    tmp_file = output_file + '.tmp'
    try:
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception:
        # Clean up tempfile on failure so it doesn't accumulate.
        try:
            os.remove(tmp_file)
        except OSError:
            pass
        raise
    os.replace(tmp_file, output_file)

    if is_partial:
        missing = len(tweets) - len(merged)
        print(
            f"⚠ Saved PARTIAL embeddings cache to {output_file} "
            f"({len(merged)}/{len(tweets)}, {missing} missing)",
            file=sys.stderr,
        )
    else:
        print(f"✓ Saved embeddings to {output_file}")


def load_tweet_embeddings_with_meta() -> Optional[Dict]:
    """Load tweet embeddings from cache file, returning embeddings + metadata.

    Returns None on both "no cache file" and "cache is corrupt" so the
    caller can fall through to regenerating from OpenAI rather than
    aborting the whole run on a bad ~370MB file. Corruption warns to
    stderr; absence is silent (cache priming on first run is expected).

    The 'partial' flag is taken from the saved file. Older caches that
    predate the field have it inferred from embedded_count vs total_tweets
    so existing files are still classified correctly after upgrade.
    """
    if not os.path.exists(DRIL_EMBEDDINGS_FILE):
        return None

    try:
        with open(DRIL_EMBEDDINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        embeddings = data['embeddings']
    except (json.JSONDecodeError, OSError, KeyError, TypeError) as e:
        print(
            f"Warning: Failed to load tweet embeddings cache "
            f"({DRIL_EMBEDDINGS_FILE}): {e}. Will regenerate.",
            file=sys.stderr,
        )
        return None

    total_tweets = data.get('total_tweets', len(embeddings))
    embedded_count = data.get('embedded_count', len(embeddings))
    if 'partial' in data:
        partial = bool(data['partial'])
    else:
        partial = embedded_count < total_tweets
    return {
        'embeddings': embeddings,
        'partial': partial,
        'total_tweets': total_tweets,
        'embedded_count': embedded_count,
    }


def load_tweet_embeddings() -> Optional[Dict[str, List[float]]]:
    """Backward-compatible wrapper: returns just the embeddings dict.

    See load_tweet_embeddings_with_meta for the partial flag and counts.
    """
    meta = load_tweet_embeddings_with_meta()
    return None if meta is None else meta['embeddings']


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    Borrowed from search_cards.py
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)

    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def calculate_popularity_scores(tweets: List[Dict]) -> Dict[str, float]:
    """
    Calculate normalized popularity scores for all tweets.

    Args:
        tweets: List of tweet dictionaries

    Returns:
        Dictionary mapping tweet_id -> normalized popularity (0-1)
    """
    # Calculate raw popularity (retweets + favorites)
    popularity_map = {}
    for tweet in tweets:
        popularity_map[tweet['id']] = tweet['retweets'] + tweet['favorites']

    # Min-max normalization
    values = list(popularity_map.values())
    min_pop = min(values) if values else 0
    max_pop = max(values) if values else 1

    normalized = {}
    for tweet_id, pop in popularity_map.items():
        if max_pop - min_pop > 0:
            normalized[tweet_id] = (pop - min_pop) / (max_pop - min_pop)
        else:
            normalized[tweet_id] = 0.0

    return normalized


def get_card_processing_order(cards: List[Dict]) -> List[str]:
    """
    Get cards in processing order: Major Arcana first, then Minor Arcana by suit.

    Args:
        cards: List of card dictionaries

    Returns:
        List of card names in processing order
    """
    card_names = [card['name'] for card in cards]
    ordered = []

    # Major Arcana first
    for card_name in MAJOR_ARCANA:
        if card_name in card_names:
            ordered.append(card_name)

    # Minor Arcana by suit
    for suit in SUITS:
        for rank in RANKS:
            card_name = f"{rank} of {suit}"
            if card_name in card_names:
                ordered.append(card_name)

    return ordered


def get_card_interpretation_text(
    card_name: str,
    position: str,
    interpretations: Dict,
    system: str
) -> str:
    """
    Get the interpretation text for a specific card, position, and system.

    Args:
        card_name: Name of the card
        position: 'upright' or 'reversed'
        interpretations: Interpretations data
        system: Interpretation system key

    Returns:
        Interpretation text
    """
    if card_name not in interpretations:
        return ""

    card_interp = interpretations[card_name]

    if system not in card_interp:
        return ""

    return card_interp[system].get(position, "")


def match_tweets_to_cards(
    cards: List[Dict],
    interpretations: Dict,
    card_embeddings: List[Dict],
    tweets: List[Dict],
    tweet_embeddings: Dict,
    system: str = 'modern_intuitive',
    min_retweets: int = 50,
    popularity_weight: float = 0.1
) -> Dict:
    """
    Match dril tweets to tarot cards with strict uniqueness constraint.

    Args:
        cards: Card data
        interpretations: Interpretation data
        card_embeddings: Card embeddings data
        tweets: Tweet data
        tweet_embeddings: Tweet embeddings
        system: Interpretation system to use
        min_retweets: Minimum retweets threshold
        popularity_weight: How much to weight popularity (0-1)

    Returns:
        Dictionary mapping card names to upright/reversed tweet matches
    """
    print(f"\nMatching tweets to cards (system: {system})")
    print("=" * 70)

    # Filter tweets by minimum retweets
    eligible_tweets = [t for t in tweets if t['retweets'] >= min_retweets]
    print(f"Eligible tweets (>={min_retweets} retweets): {len(eligible_tweets)}/{len(tweets)}")

    if len(eligible_tweets) < 156:
        print(f"\nWarning: Only {len(eligible_tweets)} eligible tweets for 156 card positions.")
        print("Consider lowering --min-retweets threshold.")

    # Calculate popularity scores
    popularity_scores = calculate_popularity_scores(tweets)

    # Track used tweets
    used_tweet_ids = set()

    # Results
    matches = {}

    # Get card processing order
    card_order = get_card_processing_order(cards)

    # Build embedding index for O(1) lookup instead of O(n) search
    embedding_index = {}
    for emb_data in card_embeddings:
        key = (emb_data['card_name'], emb_data['position'],
               emb_data.get('interpretation_system', 'combined'))
        embedding_index[key] = emb_data['embedding']

    # Build the eligible-tweet matrix once. Filter to tweets that actually
    # have an embedding so the row index matches the candidate list. The
    # original implementation re-wrapped each tweet vector as np.array on
    # every of the ~1.4M iterations; here we stack once and row-normalize
    # so each card scoring pass is a single (D,) @ (M,D)^T = (M,) matmul.
    candidate_tweets = [t for t in eligible_tweets if t['id'] in tweet_embeddings]
    if candidate_tweets:
        tweet_matrix = np.asarray(
            [tweet_embeddings[t['id']] for t in candidate_tweets],
            dtype=np.float64,
        )
        tweet_norms = np.linalg.norm(tweet_matrix, axis=1)
        # Avoid division-by-zero: zero-norm rows score 0 (matches the
        # cosine_similarity guard) and stay 0 after normalization.
        safe_tweet_norms = np.where(tweet_norms == 0, 1.0, tweet_norms)
        tweet_matrix_normed = tweet_matrix / safe_tweet_norms[:, None]
        tweet_matrix_normed[tweet_norms == 0] = 0.0
        popularity_array = np.array(
            [popularity_scores.get(t['id'], 0.0) for t in candidate_tweets],
            dtype=np.float64,
        )
    else:
        tweet_matrix_normed = np.empty((0, 0), dtype=np.float64)
        popularity_array = np.empty((0,), dtype=np.float64)

    candidate_ids = [t['id'] for t in candidate_tweets]
    id_to_index = {tid: i for i, tid in enumerate(candidate_ids)}
    available_mask = np.ones(len(candidate_tweets), dtype=bool)

    # Process each card
    for card_name in card_order:
        matches[card_name] = {}

        # Process upright, then reversed
        for position in ['upright', 'reversed']:
            # Find card embedding for this system and position using index
            card_embedding = embedding_index.get((card_name, position, system))

            if card_embedding is None:
                print(f"✗ No embedding found for {card_name} ({position}, {system})", file=sys.stderr)
                continue

            if not candidate_tweets or not available_mask.any():
                print(f"✗ No available tweet for {card_name} ({position})")
                continue

            card_vec = np.asarray(card_embedding, dtype=np.float64)
            card_norm = np.linalg.norm(card_vec)
            if card_norm == 0:
                similarities = np.zeros(len(candidate_tweets), dtype=np.float64)
            else:
                similarities = tweet_matrix_normed @ (card_vec / card_norm)
            adjusted = (
                similarities * (1.0 - popularity_weight)
                + popularity_array * popularity_weight
            )
            # Mask out used tweets so they cannot win the argmax. -inf is
            # safe because adjusted is bounded by max(|sim|, |pop|) <= ~1.
            masked = np.where(available_mask, adjusted, -np.inf)
            best_idx = int(np.argmax(masked))
            if not np.isfinite(masked[best_idx]):
                print(f"✗ No available tweet for {card_name} ({position})")
                continue

            best_tweet = candidate_tweets[best_idx]
            best_similarity = float(similarities[best_idx])
            best_score = float(adjusted[best_idx])

            # Mark as used
            used_tweet_ids.add(best_tweet['id'])
            available_mask[best_idx] = False

            # Get interpretation text
            interp_text = get_card_interpretation_text(
                card_name, position, interpretations, system
            )

            # Store match
            matches[card_name][position] = {
                'tweet_id': best_tweet['id'],
                'tweet_content': best_tweet['content'],
                'tweet_url': best_tweet['url'],
                'tweet_date': best_tweet['date'],
                'retweets': best_tweet['retweets'],
                'favorites': best_tweet['favorites'],
                'similarity_score': float(best_similarity),
                'adjusted_score': float(best_score),
                'card_interpretation': interp_text
            }

            # Display progress
            rt_k = best_tweet['retweets'] // 1000
            content_preview = best_tweet['content'][:50]
            if len(best_tweet['content']) > 50:
                content_preview += "..."

            print(f"{card_name:25s} ({position:8s}) → \"{content_preview}\" "
                  f"[sim: {best_similarity:.2f}, {rt_k}k RT]")

    return matches


def save_results(matches: Dict, output_file: str, system: str, min_retweets: int, popularity_weight: float) -> None:
    """Save matching results to JSON file"""
    # Count matches
    total_matches = sum(len(positions) for positions in matches.values())

    output = {
        'metadata': {
            'generated_at': datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z'),
            'interpretation_system': system,
            'min_retweets': min_retweets,
            'popularity_weight': popularity_weight,
            'total_cards': len(matches),
            'total_matches': total_matches
        },
        'cards': matches
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Matched {total_matches} cards to unique tweets")
    print(f"✓ Saved to {output_file}")


def main() -> None:
    """Main execution"""
    parser = argparse.ArgumentParser(
        description='Match dril tweets to tarot cards using semantic similarity',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s
  %(prog)s --system jungian_psychological
  %(prog)s --min-retweets 100 --popularity-weight 0.2
  %(prog)s --regenerate-embeddings
        '''
    )

    parser.add_argument(
        '--system',
        choices=['rws_traditional', 'thoth_crowley', 'jungian_psychological', 'modern_intuitive'],
        default='modern_intuitive',
        help='Interpretation system to use for matching (default: modern_intuitive)'
    )
    parser.add_argument(
        '--min-retweets',
        type=int,
        default=50,
        metavar='N',
        help='Minimum tweet retweets threshold (default: 50)'
    )
    parser.add_argument(
        '--popularity-weight',
        type=float,
        default=0.1,
        metavar='W',
        help='Popularity weighting factor 0.0-1.0 (default: 0.1)'
    )
    parser.add_argument(
        '--output',
        default=DEFAULT_OUTPUT_FILE,
        metavar='FILE',
        help=f'Output file path (default: {DEFAULT_OUTPUT_FILE})'
    )
    parser.add_argument(
        '--regenerate-embeddings',
        action='store_true',
        help='Force regenerate tweet embeddings cache'
    )

    args = parser.parse_args()

    # Validate popularity weight
    if not 0.0 <= args.popularity_weight <= 1.0:
        print("Error: --popularity-weight must be between 0.0 and 1.0", file=sys.stderr)
        sys.exit(1)

    try:
        # Load API key
        api_key = load_api_key()
        client = OpenAI(api_key=api_key)

        # Load data
        print("Loading data...")
        cards = load_cards()
        interpretations = load_interpretations()
        card_embeddings = load_card_embeddings()
        tweets = load_dril_tweets()

        print(f"✓ Loaded {len(cards)} cards")
        print(f"✓ Loaded {len(tweets)} dril tweets")

        # Load or generate tweet embeddings.
        tweet_embeddings = None
        if not args.regenerate_embeddings and os.path.exists(DRIL_EMBEDDINGS_FILE):
            print("\nLoading cached tweet embeddings...")
            cached = load_tweet_embeddings_with_meta()
            if cached is not None:
                tweet_embeddings = cached['embeddings']
                print(f"✓ Loaded {len(tweet_embeddings)} cached embeddings")
                if cached['partial']:
                    print(
                        f"⚠ Cache is marked PARTIAL "
                        f"({cached['embedded_count']}/{cached['total_tweets']} embedded). "
                        f"A previous run failed mid-batch.",
                        file=sys.stderr,
                    )

        # Regenerate when the user asked, when no cache exists, or when
        # the cache failed to load (load_tweet_embeddings returns None
        # on corruption and already warns to stderr).
        if tweet_embeddings is None:
            tweet_embeddings = generate_tweet_embeddings(client, tweets)
            save_tweet_embeddings(tweet_embeddings, tweets, DRIL_EMBEDDINGS_FILE)
        else:
            # Auto-retry only the tweets missing from the cache. This handles
            # both legacy partial caches and the case where new tweets were
            # added to the CSV since the cache was last built.
            missing = [t for t in tweets if t['id'] not in tweet_embeddings]
            if missing:
                print(
                    f"\n{len(missing)} tweet(s) missing from cache; "
                    f"fetching embeddings for them now...",
                    file=sys.stderr,
                )
                new_embeddings = generate_tweet_embeddings(client, missing)
                tweet_embeddings = {**tweet_embeddings, **new_embeddings}
                save_tweet_embeddings(new_embeddings, tweets, DRIL_EMBEDDINGS_FILE)

        # Match tweets to cards
        matches = match_tweets_to_cards(
            cards,
            interpretations,
            card_embeddings,
            tweets,
            tweet_embeddings,
            system=args.system,
            min_retweets=args.min_retweets,
            popularity_weight=args.popularity_weight
        )

        # Save results
        save_results(matches, args.output, args.system, args.min_retweets, args.popularity_weight)

        print("\n" + "=" * 70)
        print("Done!")
        print("=" * 70)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
