# Dril Tarot

Semantic matching of dril tweets to tarot cards using OpenAI embeddings.

## Overview

This project matches ~8,900 dril tweets to the 78 tarot cards (upright and reversed positions) using semantic similarity. Each of the 156 card positions gets matched to a unique dril tweet that captures its essence.

## Features

- **Semantic matching**: Uses OpenAI embeddings to find tweets that match card meanings
- **Configurable systems**: Match against Traditional, Crowley, Jungian, or Modern interpretations
- **Popularity weighting**: Balance semantic similarity with tweet virality
- **Strict uniqueness**: Each tweet used exactly once across all 156 positions
- **Visual gallery generation**: (Coming soon) Generate composite images of cards with tweets

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browser (for gallery generation)
playwright install chromium

# Set OpenAI API key
export OPENAI_API_KEY='your-key-here'
# Or add to ~/.env file
```

## Usage

### Generate Tweet Matches

```bash
# Basic usage (modern_intuitive system by default)
python3 match_dril_tweets.py

# Use different interpretation system
python3 match_dril_tweets.py --system jungian_psychological

# Adjust popularity weighting
python3 match_dril_tweets.py --min-retweets 100 --popularity-weight 0.2

# Force regenerate tweet embeddings
python3 match_dril_tweets.py --regenerate-embeddings
```

### Generate Gallery Images

```bash
# Download RWS tarot cards and generate all images
python3 generate_dril_tarot_images.py --download-cards

# Use existing tarot card images
python3 generate_dril_tarot_images.py --card-images-dir ./my-cards

# Resume interrupted generation
python3 generate_dril_tarot_images.py --skip-existing

# Specify output directory
python3 generate_dril_tarot_images.py --output my-gallery
```

This generates 156 composite PNG images combining:
- Public domain Rider-Waite Smith tarot cards (1909)
- Classic Twitter-styled dril tweet mockups
- Centered composition, 1200px tall, high quality

Output: `gallery/the-fool-upright.png` through `gallery/king-of-pentacles-reversed.png`

## Data Files

- `data/driltweets.csv` - Corpus of ~8,900 dril tweets with metadata
- `data/dril_tweet_embeddings.json` - Cached tweet embeddings (370MB, auto-generated)
- `data/card_dril_mapping.json` - Generated matches between cards and tweets

## Example Matches

- **The Fool (upright)**: "inventing a new Suit of playing cards: 'The Horseshoes'..."
- **The Fool (reversed)**: "FOOL: Love to get a bee in my bonnet..."
- **Death (reversed)**: "❒Single ❒Taken GenderDead"
- **The Tower (reversed)**: "my greatest sin is that I've utterly betrayed my 'NO FEAR' tower decal..."
- **The Magician (upright)**: "i got a big ass and i know how to fuck it. Mastercard"

## Gallery Examples

Once generated, you'll have beautiful composite images like:
- The Fool (upright) + "inventing a new Suit of playing cards..."
- Death (reversed) + "❒Single ❒Taken GenderDead"
- The Tower (reversed) + "betrayed my 'NO FEAR' tower decal"

## Requirements

This project uses the [semantic-tarot](https://github.com/yourusername/semantic-tarot) project as a submodule for:
- Tarot card data and interpretations
- Card embeddings for semantic matching
- Core embedding functionality

## Design Documents

See `docs/plans/` for detailed design documents:
- [Dril Tweet Matcher Design](docs/plans/2025-12-12-dril-tweet-matcher-design.md)
- [Gallery Image Generator Design](docs/plans/2025-12-12-dril-tarot-gallery-design.md)

## License

MIT License - see LICENSE file for details

Dril tweets are from [@dril](https://twitter.com/dril) and remain their copyright.
