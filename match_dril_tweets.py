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
from datetime import datetime
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
    with open(CARDS_FILE, 'r') as f:
        return json.load(f)


def load_interpretations() -> Dict:
    """Load interpretation data"""
    with open(INTERPRETATIONS_FILE, 'r') as f:
        return json.load(f)


def load_card_embeddings() -> List[Dict]:
    """Load pre-generated card embeddings"""
    if not os.path.exists(CARD_EMBEDDINGS_FILE):
        raise FileNotFoundError(
            f"Card embeddings file not found: {CARD_EMBEDDINGS_FILE}\n"
            "Please run generate_embeddings.py first to create embeddings."
        )

    with open(CARD_EMBEDDINGS_FILE, 'r') as f:
        return json.load(f)


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
                tweet = {
                    'id': row['id'],
                    'content': row['content'],
                    'date': row['date'],
                    'url': row['link'],
                    'retweets': int(row['retweets']) if row['retweets'] else 0,
                    'favorites': int(row['favorites']) if row['favorites'] else 0,
                }
                tweets.append(tweet)
            except (ValueError, KeyError) as e:
                print(f"Warning: Skipping malformed tweet row: {e}", file=sys.stderr)
                continue

    return tweets


def generate_tweet_embeddings(client: OpenAI, tweets: List[Dict]) -> Dict:
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
            # Continue with remaining batches

    print(f"✓ Generated {len(embeddings)} tweet embeddings")
    return embeddings


def save_tweet_embeddings(embeddings: Dict, tweets: List[Dict], output_file: str):
    """Save tweet embeddings to cache file"""
    data = {
        'model': 'text-embedding-3-small',
        'dimension': 1536,
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'total_tweets': len(embeddings),
        'embeddings': embeddings
    }

    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"✓ Saved embeddings to {output_file}")


def load_tweet_embeddings() -> Dict:
    """Load tweet embeddings from cache file"""
    if not os.path.exists(DRIL_EMBEDDINGS_FILE):
        return None

    with open(DRIL_EMBEDDINGS_FILE, 'r') as f:
        data = json.load(f)

    return data['embeddings']


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

    # Process each card
    for card_name in card_order:
        matches[card_name] = {}

        # Process upright, then reversed
        for position in ['upright', 'reversed']:
            # Find card embedding for this system and position
            card_embedding = None
            for emb_data in card_embeddings:
                if (emb_data['card_name'] == card_name and
                    emb_data['position'] == position and
                    emb_data.get('interpretation_system', 'combined') == system):
                    card_embedding = emb_data['embedding']
                    break

            if card_embedding is None:
                print(f"✗ No embedding found for {card_name} ({position}, {system})")
                continue

            # Find best matching tweet
            best_tweet = None
            best_score = -1.0
            best_similarity = 0.0

            for tweet in eligible_tweets:
                # Skip if already used
                if tweet['id'] in used_tweet_ids:
                    continue

                # Skip if no embedding
                if tweet['id'] not in tweet_embeddings:
                    continue

                # Calculate similarity
                tweet_emb = tweet_embeddings[tweet['id']]
                similarity = cosine_similarity(card_embedding, tweet_emb)

                # Apply popularity weighting
                popularity = popularity_scores.get(tweet['id'], 0.0)
                adjusted_score = similarity * (1 - popularity_weight) + popularity * popularity_weight

                if adjusted_score > best_score:
                    best_score = adjusted_score
                    best_similarity = similarity
                    best_tweet = tweet

            if best_tweet is None:
                print(f"✗ No available tweet for {card_name} ({position})")
                continue

            # Mark as used
            used_tweet_ids.add(best_tweet['id'])

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


def save_results(matches: Dict, output_file: str, system: str, min_retweets: int, popularity_weight: float):
    """Save matching results to JSON file"""
    # Count matches
    total_matches = sum(len(positions) for positions in matches.values())

    output = {
        'metadata': {
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'interpretation_system': system,
            'min_retweets': min_retweets,
            'popularity_weight': popularity_weight,
            'total_cards': len(matches),
            'total_matches': total_matches
        },
        'cards': matches
    }

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Matched {total_matches} cards to unique tweets")
    print(f"✓ Saved to {output_file}")


def main():
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

        # Load or generate tweet embeddings
        if args.regenerate_embeddings or not os.path.exists(DRIL_EMBEDDINGS_FILE):
            tweet_embeddings = generate_tweet_embeddings(client, tweets)
            save_tweet_embeddings(tweet_embeddings, tweets, DRIL_EMBEDDINGS_FILE)
        else:
            print("\nLoading cached tweet embeddings...")
            tweet_embeddings = load_tweet_embeddings()
            print(f"✓ Loaded {len(tweet_embeddings)} cached embeddings")

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
