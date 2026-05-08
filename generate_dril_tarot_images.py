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
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from PIL import Image
from playwright.sync_api import sync_playwright
import requests
from urllib.parse import quote

# sanitize_filename has a single canonical definition in download_tarot_cards
# so a fix or extension (length caps, non-ASCII handling, etc.) cannot drift
# between the writer (downloader) and the reader (gallery + verifier).
from download_tarot_cards import sanitize_filename

# Configuration
CARD_MAPPING_FILE = 'data/card_dril_mapping.json'
SEMANTIC_TAROT_DIR = 'semantic-tarot'
DEFAULT_OUTPUT_DIR = 'gallery'
DEFAULT_CARDS_DIR = 'tarot-cards'
TWEET_SCREENSHOTS_CACHE = 'data/tweet_screenshots_cache.json'
VIEWPORT_WIDTH = 600
VIEWPORT_HEIGHT = 800


def load_card_mapping() -> Dict:
    """Load card-to-tweet mapping data"""
    if not os.path.exists(CARD_MAPPING_FILE):
        raise FileNotFoundError(
            f"Card mapping not found: {CARD_MAPPING_FILE}\n"
            "Run match_dril_tweets.py first to generate mappings."
        )

    with open(CARD_MAPPING_FILE, 'r', encoding='utf-8') as f:
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

    # Base64 encoded dril avatar (actual profile picture)
    avatar_placeholder = "data:image/jpeg;base64,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"

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
            <img class="avatar" src="{avatar_placeholder}" alt="wint">
            <div class="user-info">
                <span class="name">wint</span>
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


def screenshot_tweet(page, tweet_data: Dict) -> bytes:
    """
    Screenshot a tweet using Playwright page.

    Args:
        page: Playwright page object (reused for efficiency)
        tweet_data: Tweet data dict

    Returns:
        PNG image bytes
    """
    # Generate HTML
    html_content = create_tweet_html(tweet_data)

    # Load HTML into page
    page.set_content(html_content)

    # Wait for content to render
    page.wait_for_selector('.tweet-card')

    # Screenshot just the tweet card element
    tweet_element = page.query_selector('.tweet-card')
    screenshot_bytes = tweet_element.screenshot(type='png')

    return screenshot_bytes


def generate_tweet_screenshots(
    mapping: Dict,
    only_for: Optional[List[Tuple[str, str]]] = None,
) -> Dict[Tuple[str, str], bytes]:
    """
    Generate tweet screenshots using Playwright.

    Args:
        mapping: Card mapping data
        only_for: Optional list of (card_name, position) pairs to render.
            When provided, only those entries are produced; the rest of
            the mapping is left alone. Used by callers that already have
            a (partially) fresh cache and only need the stale entries
            regenerated, rather than reflowing all 156 cards.

    Returns:
        Dict mapping (card_name, position) -> screenshot PNG bytes
    """
    screenshots = {}

    if only_for is None:
        targets = get_card_processing_order(mapping)
    else:
        targets = list(only_for)

    if not targets:
        print(f"\n✓ No tweet screenshots to generate (cache is fully fresh)")
        return screenshots

    print(f"\nGenerating tweet screenshots ({len(targets)} entries)...")

    try:
        with sync_playwright() as p:
            # Launch browser (headless)
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={'width': VIEWPORT_WIDTH, 'height': VIEWPORT_HEIGHT})

                for i, (card_name, position) in enumerate(targets, 1):
                    tweet_data = mapping['cards'][card_name][position]

                    try:
                        # Screenshot
                        screenshot_bytes = screenshot_tweet(page, tweet_data)
                        screenshots[(card_name, position)] = screenshot_bytes

                        # Progress - show every 10 screenshots
                        if i % 10 == 0:
                            print(f"  Progress: {i}/{len(targets)} tweets...")
                    except Exception as e:
                        print(f"  ✗ Failed {card_name} ({position}): {e}", file=sys.stderr)
                        # Continue with others

            finally:
                browser.close()
    except Exception as e:
        print(f"\n✗ Playwright error: {e}", file=sys.stderr)
        print("Make sure Playwright is installed: playwright install chromium", file=sys.stderr)
        raise

    print(f"✓ Generated {len(screenshots)} tweet screenshots")
    return screenshots


def _mapping_tweet_id(mapping: Dict, card_name: str, position: str) -> Optional[str]:
    """Pull the tweet_id for a (card, position) out of a mapping dict."""
    try:
        return mapping['cards'][card_name][position].get('tweet_id')
    except (KeyError, AttributeError, TypeError):
        return None


def cache_screenshots(
    screenshots: Dict[Tuple[str, str], bytes],
    mapping: Optional[Dict] = None,
) -> None:
    """Cache tweet screenshots to disk, tagged by tweet_id.

    Each entry stores the tweet_id from the current mapping alongside the
    PNG bytes. On reload, any entry whose stored tweet_id no longer matches
    the active mapping is treated as stale -- so changing --system,
    --min-retweets, or hand-editing card_dril_mapping.json invalidates only
    the affected screenshots instead of silently serving the previous run's
    images for the new card-tweet assignments.
    """
    import base64

    cache_data = {}
    for (card_name, position), screenshot_bytes in screenshots.items():
        key = f"{card_name}|{position}"
        tweet_id = _mapping_tweet_id(mapping, card_name, position) if mapping else None
        cache_data[key] = {
            'tweet_id': tweet_id,
            'data': base64.b64encode(screenshot_bytes).decode('utf-8'),
        }

    os.makedirs(os.path.dirname(TWEET_SCREENSHOTS_CACHE), exist_ok=True)

    # Atomic write: don't truncate a previous valid cache if json.dump fails
    # halfway through.
    tmp = TWEET_SCREENSHOTS_CACHE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f)
    os.replace(tmp, TWEET_SCREENSHOTS_CACHE)

    print(f"✓ Cached {len(screenshots)} screenshots to {TWEET_SCREENSHOTS_CACHE}")


def load_cached_screenshots(
    mapping: Optional[Dict] = None,
) -> Optional[Dict[Tuple[str, str], bytes]]:
    """Load cached screenshots, filtering stale entries against `mapping`.

    Cache schema is `{ "<card>|<position>": {"tweet_id": str, "data": b64} }`.
    Older caches that store `{ "<card>|<position>": "<b64>" }` directly
    have no tweet_id sidecar -- they cannot be validated, so they are
    treated as fully stale and an empty dict is returned (callers will
    regenerate). When `mapping` is None, freshness cannot be checked and
    only the entries that have a stored tweet_id are returned (still as
    bytes).
    """
    import base64

    if not os.path.exists(TWEET_SCREENSHOTS_CACHE):
        return None

    try:
        with open(TWEET_SCREENSHOTS_CACHE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Warning: Failed to load screenshot cache: {e}", file=sys.stderr)
        return None

    screenshots: Dict[Tuple[str, str], bytes] = {}
    stale_count = 0
    legacy_count = 0
    for key, entry in cache_data.items():
        parts = key.split('|', 1)
        if len(parts) != 2:
            print(f"Warning: Invalid cache key format: {key}", file=sys.stderr)
            continue
        card_name, position = parts

        # Legacy format: bare base64 string with no tweet_id metadata. We
        # can't tell whether this was rendered for the current mapping or
        # an older one, so refuse to serve it.
        if not isinstance(entry, dict):
            legacy_count += 1
            continue

        stored_tweet_id = entry.get('tweet_id')
        b64_data = entry.get('data')
        if b64_data is None:
            continue

        if mapping is not None:
            current_tweet_id = _mapping_tweet_id(mapping, card_name, position)
            # Drop the entry when we have a current assignment to compare
            # against and it doesn't match what was originally rendered.
            if current_tweet_id is not None and stored_tweet_id != current_tweet_id:
                stale_count += 1
                continue

        try:
            screenshots[(card_name, position)] = base64.b64decode(b64_data)
        except (ValueError, TypeError) as e:
            print(f"Warning: Bad b64 for {key}: {e}", file=sys.stderr)
            continue

    if legacy_count:
        print(
            f"Warning: discarded {legacy_count} legacy screenshot cache "
            f"entries (no tweet_id sidecar -- will regenerate)",
            file=sys.stderr,
        )
    if stale_count:
        print(
            f"Note: {stale_count} cached screenshot(s) stale due to "
            f"mapping change -- will regenerate just those",
            file=sys.stderr,
        )

    return screenshots


def download_rws_cards(output_dir: str) -> bool:
    """
    Download public domain Rider-Waite Smith tarot card images from
    Internet Archive.

    Delegates to download_tarot_cards.download_cards, which fetches the 1909
    Pamela Colman Smith illustrations directly. The earlier implementation
    only printed manual-download instructions and blocked on input(), which
    contradicted the --download-cards flag's name.

    Args:
        output_dir: Directory to save card images

    Returns:
        True if all 78 cards were downloaded (or already cached), else False.
    """
    import download_tarot_cards
    return download_tarot_cards.download_cards(output_dir=output_dir)


def verify_card_images(cards_dir: str) -> Tuple[bool, List[str]]:
    """
    Verify all 78 tarot card images are present.

    Returns:
        (success, missing_cards)
    """
    # Load card names from mapping
    with open(CARD_MAPPING_FILE, 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    card_names = list(mapping['cards'].keys())
    missing = []

    for card_name in card_names:
        filename = sanitize_filename(card_name) + '.jpg'
        path = os.path.join(cards_dir, filename)

        if not os.path.exists(path):
            missing.append(card_name)

    return len(missing) == 0, missing


def composite_tweet_on_card(
    card_image_path: str,
    tweet_screenshot_bytes: bytes,
    card_name: str,
    position: str
) -> Image.Image:
    """
    Composite tweet screenshot onto tarot card image.

    Args:
        card_image_path: Path to tarot card JPG
        tweet_screenshot_bytes: PNG bytes of tweet
        card_name: Card name (for reversed handling)
        position: 'upright' or 'reversed'

    Returns:
        Composite PIL Image
    """
    # Load card image
    card = Image.open(card_image_path)

    # Validate dimensions
    if card.width == 0 or card.height == 0:
        raise ValueError(f"Invalid card image dimensions: {card.size}")
    if card.width > 10000 or card.height > 10000:
        raise ValueError(f"Card image too large: {card.size}")

    # Convert to RGB if necessary (in case of RGBA or other modes)
    if card.mode != 'RGB':
        card = card.convert('RGB')

    # Standardize card size (maintain aspect ratio, fit to height)
    target_height = 1200
    aspect_ratio = card.width / card.height
    target_width = int(target_height * aspect_ratio)
    card = card.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # Rotate if reversed
    if position == 'reversed':
        card = card.rotate(180)

    # Load tweet screenshot
    tweet_img = Image.open(BytesIO(tweet_screenshot_bytes))

    # Calculate center position
    card_width, card_height = card.size
    tweet_width, tweet_height = tweet_img.size

    # Center horizontally and vertically
    x = (card_width - tweet_width) // 2
    y = (card_height - tweet_height) // 2

    # Paste tweet onto card. If the tweet PNG has an alpha channel (it
    # usually does: the CSS border-radius creates transparent corners), use
    # it as the paste mask so those corners let the tarot card show through
    # rather than being painted as opaque RGB.
    if tweet_img.mode in ('RGBA', 'LA'):
        card.paste(tweet_img, (x, y), tweet_img)
    else:
        card.paste(tweet_img, (x, y))

    return card


def generate_gallery_images(
    mapping: Dict,
    cards_dir: str,
    output_dir: str,
    skip_existing: bool = False,
    regenerate_screenshots: bool = False
):
    """
    Generate all 156 gallery images.

    Args:
        mapping: Card mapping data
        cards_dir: Directory with tarot card images
        output_dir: Output directory for gallery
        skip_existing: Skip if output file exists
        regenerate_screenshots: Force regenerate screenshots (ignore cache)
    """
    print("\nGenerating gallery images...")
    print("=" * 70)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Try to load cached screenshots if not regenerating. Pass the active
    # mapping so any cached entry whose tweet_id no longer matches the
    # current assignment is dropped before we use it (dril-tarot-41z).
    screenshots: Optional[Dict[Tuple[str, str], bytes]] = None
    if not regenerate_screenshots:
        print("\nChecking for cached screenshots...")
        screenshots = load_cached_screenshots(mapping)
        if screenshots:
            print(f"✓ Loaded {len(screenshots)} cached screenshots")
        else:
            print("No fresh cache entries, generating screenshots...")

    if screenshots is None:
        screenshots = {}

    # Compute which (card, position) pairs the current mapping needs but the
    # cache cannot satisfy. Regenerate ONLY those, then merge with the cache
    # so a single mapping change doesn't reflow all 156 screenshots.
    needed_pairs = get_card_processing_order(mapping)
    missing_pairs = [pair for pair in needed_pairs if pair not in screenshots]

    if missing_pairs:
        new_screenshots = generate_tweet_screenshots(mapping, only_for=missing_pairs)
        screenshots.update(new_screenshots)
        # Persist the merged cache (cached + freshly regenerated). cache_screenshots
        # is given the mapping so each entry is tagged with its tweet_id for the
        # next run's freshness check.
        cache_screenshots(screenshots, mapping)

    # Process each card
    cards = get_card_processing_order(mapping)

    for i, (card_name, position) in enumerate(cards, 1):
        # Output filename
        output_filename = sanitize_filename(card_name) + f'-{position}.png'
        output_path = os.path.join(output_dir, output_filename)

        # Skip if exists
        if skip_existing and os.path.exists(output_path):
            print(f"[{i}/{len(cards)}] {card_name} ({position}) - skipped (exists)")
            continue

        # Get tweet screenshot; may be absent if an earlier screenshot step
        # failed (generate_tweet_screenshots logs and continues) or if the
        # cache file is incomplete. Skip rather than aborting the whole run.
        screenshot_bytes = screenshots.get((card_name, position))
        if screenshot_bytes is None:
            print(
                f"[{i}/{len(cards)}] {card_name} ({position}) - skipped "
                f"(no screenshot available)",
                file=sys.stderr,
            )
            continue

        # Get card image path
        card_image_filename = sanitize_filename(card_name) + '.jpg'
        card_image_path = os.path.join(cards_dir, card_image_filename)

        # Composite + save. Per-card failures (corrupt card image, unexpected
        # PIL mode, transient disk error) must not abort the whole run -- the
        # cached-screenshots phase has already succeeded by this point and
        # the user has invested setup time. Mirror generate_tweet_screenshots'
        # log-and-continue pattern.
        try:
            composite = composite_tweet_on_card(
                card_image_path,
                screenshot_bytes,
                card_name,
                position
            )

            # compress_level=6: default compression (0-9, higher = smaller file but slower)
            # optimize=True: enables PNG optimization for smaller file size
            composite.save(output_path, 'PNG', compress_level=6, optimize=True)
        except Exception as e:
            print(
                f"[{i}/{len(cards)}] {card_name} ({position}) - failed: {e}",
                file=sys.stderr,
            )
            continue

        print(f"[{i}/{len(cards)}] {card_name} ({position}) → {output_filename}")

    print("\n" + "=" * 70)
    print(f"✓ Generated {len(cards)} gallery images in {output_dir}/")


def test_tweet_html() -> None:
    """Test function to preview tweet HTML"""
    sample_tweet = {
        'tweet_content': 'inventing a new Suit of playing cards: "The Horseshoes" - We got the king, queen, jack and Ace. All your favorites - The most powerful suit',
        'tweet_date': '2018-05-03 20:06:45',
        'retweets': 599,
        'favorites': 5543
    }

    html_output = create_tweet_html(sample_tweet)

    # Save to temp file for manual inspection
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html_output)
        temp_path = f.name

    print(f"✓ Test HTML saved to {temp_path}")
    print("  Open in browser to preview tweet styling")


def check_playwright_installed() -> bool:
    """Check if Playwright browsers are installed"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Try to launch browser
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception as e:
        return False


def main() -> None:
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
    parser.add_argument(
        '--regenerate-screenshots',
        action='store_true',
        help='Force regenerate tweet screenshots (ignore cache)'
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

        # Check Playwright
        if not check_playwright_installed():
            print("\n✗ Playwright not installed or browsers not available")
            print("Install with: playwright install chromium")
            sys.exit(1)

        # Handle tarot card images
        if args.download_cards:
            success = download_rws_cards(args.card_images_dir)
            if not success:
                print("\n✗ Card download incomplete", file=sys.stderr)
                sys.exit(1)

        # Verify cards present
        print(f"\nVerifying tarot card images in {args.card_images_dir}/...")
        cards_ok, missing = verify_card_images(args.card_images_dir)

        if not cards_ok:
            print(f"✗ Missing {len(missing)} card images:", file=sys.stderr)
            for card in missing[:5]:
                print(f"  - {card}", file=sys.stderr)
            if len(missing) > 5:
                print(f"  ... and {len(missing) - 5} more", file=sys.stderr)
            print(f"\nRun with --download-cards to download them", file=sys.stderr)
            sys.exit(1)

        print(f"✓ All 78 tarot card images present")

        # Generate gallery
        generate_gallery_images(
            mapping,
            args.card_images_dir,
            args.output,
            args.skip_existing,
            args.regenerate_screenshots
        )

        print("\n" + "=" * 70)
        print("Gallery generation complete!")
        print(f"Images saved to: {args.output}/")
        print("=" * 70)

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
