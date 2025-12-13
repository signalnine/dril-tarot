# Dril Tweet Tarot Matcher - Design Document

**Date:** 2025-12-12
**Status:** Approved

## Overview

A standalone script that matches dril tweets to tarot cards using semantic similarity and OpenAI embeddings. Each of the 78 tarot cards will be matched to two dril tweets (one for upright position, one for reversed), ensuring strict uniqueness (156 total unique matches).

## Architecture

### Core Components

1. **match_dril_tweets.py** - Main script that:
   - Loads dril tweets, cards, and interpretations
   - Generates/loads tweet embeddings (cached)
   - Matches tweets to cards using semantic similarity + popularity weighting
   - Outputs rich JSON mapping with metadata

2. **Tweet embedding cache** - `dril_tweet_embeddings.json`
   - ~8,900 tweet embeddings using text-embedding-3-small
   - Auto-generated on first run (~$0.02 cost)
   - Reusable for future matching runs with different parameters

3. **Output file** - `card_dril_mapping.json`
   - 156 card-tweet matches with full metadata
   - Includes similarity scores, tweet stats, timestamps

### Data Flow

```
driltweets.csv ──→ Tweet Embeddings ──┐
                   (cached)           │
                                      ├──→ Similarity Matching ──→ card_dril_mapping.json
cards.json + interpretations.json ──→ │
card_embeddings.json ────────────────┘
```

## Matching Algorithm

### Process (for each card position)

1. **Calculate base similarity** - Cosine similarity between card embedding and all tweet embeddings
2. **Apply popularity boost** - Adjust scores based on retweets + favorites
   ```python
   adjusted_score = similarity * (1 - weight) + normalized_popularity * weight
   ```
3. **Filter by threshold** - Remove tweets below minimum retweets (default: 50)
4. **Select best available** - Pick highest-scoring unused tweet
5. **Mark as used** - Remove from pool for strict uniqueness

### Configuration Flags

- `--system <name>` - Interpretation system (default: modern_intuitive)
  - Options: rws_traditional, thoth_crowley, jungian_psychological, modern_intuitive
- `--min-retweets <n>` - Minimum tweet popularity (default: 50)
- `--popularity-weight <float>` - Popularity influence 0.0-1.0 (default: 0.1)
- `--output <path>` - Output file (default: card_dril_mapping.json)
- `--regenerate-embeddings` - Force rebuild of tweet embedding cache

### Processing Order

To ensure fair distribution with strict uniqueness:

1. Major Arcana (The Fool → The World)
   - Upright positions first
   - Then reversed positions
2. Minor Arcana by suit (Wands, Cups, Swords, Pentacles)
   - Ace → King for each suit
   - Upright then reversed

This gives "important" cards first choice of best matches.

## Output Format

### card_dril_mapping.json Structure

```json
{
  "metadata": {
    "generated_at": "2025-12-12T10:30:00Z",
    "interpretation_system": "modern_intuitive",
    "min_retweets": 50,
    "popularity_weight": 0.1,
    "total_cards": 78,
    "total_matches": 156
  },
  "cards": {
    "The Fool": {
      "upright": {
        "tweet_id": "922321981",
        "tweet_content": "no",
        "tweet_url": "https://twitter.com/dril/status/922321981",
        "tweet_date": "2008-09-15 19:25:20",
        "retweets": 59552,
        "favorites": 114638,
        "similarity_score": 0.823,
        "adjusted_score": 0.845,
        "card_interpretation": "Immaturity, sincerity, a free spirit..."
      },
      "reversed": {
        "tweet_id": "...",
        "tweet_content": "...",
        "tweet_url": "...",
        "tweet_date": "...",
        "retweets": 0,
        "favorites": 0,
        "similarity_score": 0.0,
        "adjusted_score": 0.0,
        "card_interpretation": "..."
      }
    }
  }
}
```

### Console Output

During matching:
```
Generating dril tweet embeddings... (this may take a minute)
✓ Generated 8,922 tweet embeddings

Matching tweets to cards (system: modern_intuitive)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The Fool (upright)        → "no" [sim: 0.82, 59k RT]
The Fool (reversed)       → "..." [sim: 0.76, 12k RT]
The Magician (upright)    → "..." [sim: 0.85, 23k RT]
...

✓ Matched 156 cards to unique tweets
✓ Saved to card_dril_mapping.json
```

## Tweet Embedding Generation

### dril_tweet_embeddings.json Structure

```json
{
  "model": "text-embedding-3-small",
  "dimension": 1536,
  "generated_at": "2025-12-12T10:00:00Z",
  "total_tweets": 8922,
  "embeddings": {
    "922321981": [0.123, -0.456, ...],
    "2299229204": [0.789, -0.234, ...],
    ...
  }
}
```

### Generation Process

1. Load `driltweets.csv` using Python's csv module
2. Parse tweets (handle commas/quotes in content properly)
3. Extract: id, content, date, retweets, favorites
4. Batch embed in groups of 100 for efficiency
5. Save to cache file

### Data Cleaning

- Keep mentions, hashtags, URLs in tweet content (part of dril's style)
- Handle missing/empty content gracefully
- Convert retweets/favorites to integers (default to 0 if missing)

## Implementation Details

### Dependencies

Add to `requirements.txt`:
- `python-dotenv` - For loading ~/.env file

Already available:
- `openai` - Embedding API
- `numpy` - Cosine similarity calculations

### OpenAI API Key Loading

```python
import os
from dotenv import load_dotenv

# Try environment variable first
api_key = os.getenv('OPENAI_API_KEY')

# Fall back to ~/.env file
if not api_key:
    load_dotenv(os.path.expanduser('~/.env'))
    api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment or ~/.env")
```

### Popularity Normalization

```python
# Calculate popularity score for each tweet
popularity_scores = [tweet['retweets'] + tweet['favorites'] for tweet in tweets]

# Min-max normalization
min_pop = min(popularity_scores)
max_pop = max(popularity_scores)
normalized = [(p - min_pop) / (max_pop - min_pop) for p in popularity_scores]
```

### Code Reuse

Borrow from existing codebase:
- `search_cards.py` - cosine_similarity() function
- `generate_embeddings.py` - OpenAI client setup, batch processing logic
- Both - JSON loading patterns

## Error Handling

- **Missing OPENAI_API_KEY** → Clear error with instructions to set env var or ~/.env
- **CSV parse errors** → Show line number and content, continue with other tweets
- **Insufficient unique tweets** → Report which card position failed (unlikely with 8,900 tweets)
- **API errors** → Retry with exponential backoff, show progress
- **Missing data files** → List which files are missing with expected paths

## Testing Strategy

- Test with small subset of tweets first (--max-tweets flag for development)
- Verify uniqueness constraint works correctly
- Test different system/weight combinations
- Validate JSON output structure
- Check edge cases (tweets with 0 retweets, empty content, etc.)

## Future Enhancements

Once basic matching works:
- Integration with tarot.py (show dril tweet with card draws)
- Web interface to browse matches
- Alternative matching strategies (e.g., GPT-4 picks the funniest match)
- Export to different formats (HTML gallery, markdown, etc.)
