#!/usr/bin/env python3
"""
Generate dril-tarot gallery images.

Combines public domain Rider-Waite Smith tarot cards with styled dril tweet
mockups to create 156 composite images for browsing.
"""

import html
import json
import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image
from playwright.sync_api import sync_playwright

# Configuration
CARD_MAPPING_FILE = 'data/card_dril_mapping.json'
SEMANTIC_TAROT_DIR = 'semantic-tarot'
DEFAULT_OUTPUT_DIR = 'gallery'
DEFAULT_CARDS_DIR = 'tarot-cards'


def load_card_mapping() -> Dict:
    """Load card-to-tweet mapping data"""
    if not os.path.exists(CARD_MAPPING_FILE):
        raise FileNotFoundError(
            f"Card mapping not found: {CARD_MAPPING_FILE}\n"
            "Run match_dril_tweets.py first to generate mappings."
        )

    with open(CARD_MAPPING_FILE, 'r') as f:
        data = json.load(f)

    return data


def get_card_processing_order(mapping: Dict) -> List[Tuple[str, str]]:
    """
    Get cards in processing order: (card_name, position).
    Returns list of tuples like [('The Fool', 'upright'), ('The Fool', 'reversed'), ...]
    """
    cards_order = []

    # Process in order from mapping
    for card_name in mapping['cards'].keys():
        for position in ['upright', 'reversed']:
            if position in mapping['cards'][card_name]:
                cards_order.append((card_name, position))

    return cards_order


def create_tweet_html(tweet_data: Dict) -> str:
    """
    Generate HTML for tweet mockup in classic Twitter style.

    Args:
        tweet_data: Dict with tweet_content, tweet_date, retweets, favorites

    Returns:
        HTML string
    """
    # Extract data
    content = tweet_data['tweet_content']
    date = tweet_data['tweet_date']
    retweets = tweet_data['retweets']
    favorites = tweet_data['favorites']

    # Format date (just the date part)
    date_display = date.split()[0] if ' ' in date else date

    # Base64 encoded small dril avatar placeholder (tiny gray circle)
    avatar_placeholder = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAA2SURBVDhPY/wPBAxUAExQmgYGoxpHNY5qHNU4qpEMQFFNDMMaKQWjGkc1jmoc1TiqcVQjAwMABtQBDZdEI0gAAAAASUVORK5CYII="

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: transparent;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}

        .tweet-card {{
            background: white;
            border: 1px solid #e1e8ed;
            border-radius: 16px;
            padding: 16px;
            max-width: 500px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        }}

        .tweet-header {{
            display: flex;
            align-items: center;
            margin-bottom: 12px;
        }}

        .avatar {{
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: #ccc;
            margin-right: 12px;
        }}

        .user-info {{
            display: flex;
            flex-direction: column;
        }}

        .name {{
            font-weight: bold;
            font-size: 15px;
            color: #14171a;
        }}

        .handle {{
            font-size: 15px;
            color: #657786;
        }}

        .tweet-body {{
            font-size: 23px;
            line-height: 1.4;
            color: #14171a;
            margin-bottom: 12px;
            word-wrap: break-word;
            white-space: pre-wrap;
        }}

        .tweet-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #657786;
            font-size: 15px;
            padding-top: 12px;
            border-top: 1px solid #e1e8ed;
        }}

        .timestamp {{
            color: #657786;
        }}

        .engagement {{
            display: flex;
            gap: 16px;
        }}

        .engagement span {{
            color: #657786;
        }}

        .rt-icon {{
            color: #17bf63;
        }}

        .like-icon {{
            color: #e0245e;
        }}
    </style>
</head>
<body>
    <div class="tweet-card">
        <div class="tweet-header">
            <img class="avatar" src="{avatar_placeholder}" alt="dril">
            <div class="user-info">
                <span class="name">dril</span>
                <span class="handle">@dril</span>
            </div>
        </div>
        <div class="tweet-body">{html.escape(content)}</div>
        <div class="tweet-footer">
            <span class="timestamp">{date_display}</span>
            <div class="engagement">
                <span class="rt-icon">🔁 {retweets:,}</span>
                <span class="like-icon">❤️ {favorites:,}</span>
            </div>
        </div>
    </div>
</body>
</html>
    """

    return html_content


def test_tweet_html():
    """Test function to preview tweet HTML"""
    sample_tweet = {
        'tweet_content': 'inventing a new Suit of playing cards: "The Horseshoes" - We got the king, queen, jack and Ace. All your favorites - The most powerful suit',
        'tweet_date': '2018-05-03 20:06:45',
        'retweets': 599,
        'favorites': 5543
    }

    html_output = create_tweet_html(sample_tweet)

    # Save to temp file for manual inspection
    with open('/tmp/tweet_preview.html', 'w') as f:
        f.write(html_output)

    print("✓ Test HTML saved to /tmp/tweet_preview.html")
    print("  Open in browser to preview tweet styling")


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(
        description='Generate dril-tarot gallery images'
    )
    parser.add_argument(
        '--download-cards',
        action='store_true',
        help='Download public domain RWS tarot card images'
    )
    parser.add_argument(
        '--card-images-dir',
        default=DEFAULT_CARDS_DIR,
        help=f'Directory containing tarot card images (default: {DEFAULT_CARDS_DIR})'
    )
    parser.add_argument(
        '--output',
        default=DEFAULT_OUTPUT_DIR,
        help=f'Output directory for gallery images (default: {DEFAULT_OUTPUT_DIR})'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip generating images that already exist'
    )

    args = parser.parse_args()

    print("Dril-Tarot Gallery Generator")
    print("=" * 70)

    try:
        # Load mapping
        print("\nLoading card-tweet mappings...")
        mapping = load_card_mapping()
        print(f"✓ Loaded {mapping['metadata']['total_matches']} card-tweet matches")

        # Get processing order
        cards = get_card_processing_order(mapping)
        print(f"✓ Will generate {len(cards)} gallery images")

    except FileNotFoundError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
