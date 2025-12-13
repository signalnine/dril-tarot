# Dril-Tarot Gallery Generator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate 156 composite images combining public domain Rider-Waite Smith tarot cards with styled dril tweet mockups for a browseable gallery.

**Architecture:** Playwright renders HTML/CSS tweet mockups to PNG screenshots. Pillow composites these onto RWS tarot card images (downloaded or user-provided), saving 156 gallery images with descriptive filenames.

**Tech Stack:** Playwright (headless browser), Pillow (image manipulation), requests (HTTP downloads), existing card_dril_mapping.json

---

## Task 1: Project Setup and Dependencies

**Files:**
- Modify: `requirements.txt`
- Create: `generate_dril_tarot_images.py`

**Step 1: Add Playwright to requirements**

Edit `requirements.txt`, add after Pillow:
```
requests>=2.31.0
```

(Playwright and Pillow already present)

**Step 2: Create script skeleton with imports**

Create `generate_dril_tarot_images.py`:
```python
#!/usr/bin/env python3
"""
Generate dril-tarot gallery images.

Combines public domain Rider-Waite Smith tarot cards with styled dril tweet
mockups to create 156 composite images for browsing.
"""

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
    print("Not yet implemented")


if __name__ == "__main__":
    main()
```

**Step 3: Make script executable and test help**

Run:
```bash
chmod +x generate_dril_tarot_images.py
python3 generate_dril_tarot_images.py --help
```

Expected: Help text displays correctly

**Step 4: Commit**

```bash
git add requirements.txt generate_dril_tarot_images.py
git commit -m "feat: add gallery generator script skeleton

- Add requests to requirements
- Create basic CLI structure with argparse
- Define configuration constants"
```

---

## Task 2: Load Card-Tweet Mapping Data

**Files:**
- Modify: `generate_dril_tarot_images.py`

**Step 1: Add data loading function**

Add after configuration constants:
```python
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
```

**Step 2: Update main() to load and display data**

Replace "Not yet implemented" in main():
```python
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
```

**Step 3: Test data loading**

Run:
```bash
cd /home/gabe/dril-tarot
python3 generate_dril_tarot_images.py
```

Expected:
```
Dril-Tarot Gallery Generator
======================================================================

Loading card-tweet mappings...
✓ Loaded 156 card-tweet matches
✓ Will generate 156 gallery images
```

**Step 4: Commit**

```bash
git add generate_dril_tarot_images.py
git commit -m "feat: load card-tweet mapping data

- Add load_card_mapping() function
- Add get_card_processing_order() for iteration
- Test data loading in main()"
```

---

## Task 3: Create Tweet HTML Template

**Files:**
- Modify: `generate_dril_tarot_images.py`

**Step 1: Add HTML template function**

Add after get_card_processing_order():
```python
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

    html = f"""
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
        <div class="tweet-body">{content}</div>
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

    return html
```

**Step 2: Add test function to preview HTML**

Add after create_tweet_html():
```python
def test_tweet_html():
    """Test function to preview tweet HTML"""
    sample_tweet = {
        'tweet_content': 'inventing a new Suit of playing cards: "The Horseshoes" - We got the king, queen, jack and Ace. All your favorites - The most powerful suit',
        'tweet_date': '2018-05-03 20:06:45',
        'retweets': 599,
        'favorites': 5543
    }

    html = create_tweet_html(sample_tweet)

    # Save to temp file for manual inspection
    with open('/tmp/tweet_preview.html', 'w') as f:
        f.write(html)

    print("✓ Test HTML saved to /tmp/tweet_preview.html")
    print("  Open in browser to preview tweet styling")
```

**Step 3: Test HTML generation**

Run:
```bash
cd /home/gabe/dril-tarot
python3 -c "from generate_dril_tarot_images import test_tweet_html; test_tweet_html()"
```

Expected: HTML file created, manually inspect in browser

**Step 4: Commit**

```bash
git add generate_dril_tarot_images.py
git commit -m "feat: add tweet HTML template generator

- Create create_tweet_html() with classic Twitter styling
- Include avatar placeholder, name, handle, timestamp
- Display retweets and favorites with icons
- Add test function for preview"
```

---

## Task 4: Implement Playwright Tweet Screenshot

**Files:**
- Modify: `generate_dril_tarot_images.py`

**Step 1: Add screenshot function**

Add after create_tweet_html():
```python
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
    html = create_tweet_html(tweet_data)

    # Load HTML into page
    page.set_content(html)

    # Wait for content to render
    page.wait_for_selector('.tweet-card')

    # Screenshot just the tweet card element
    tweet_element = page.query_selector('.tweet-card')
    screenshot_bytes = tweet_element.screenshot(type='png')

    return screenshot_bytes


def generate_tweet_screenshots(mapping: Dict) -> Dict[Tuple[str, str], bytes]:
    """
    Generate all tweet screenshots using Playwright.

    Args:
        mapping: Card mapping data

    Returns:
        Dict mapping (card_name, position) -> screenshot PNG bytes
    """
    screenshots = {}

    print("\nGenerating tweet screenshots...")

    with sync_playwright() as p:
        # Launch browser (headless)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 600, 'height': 800})

        # Process each card
        cards = get_card_processing_order(mapping)
        for i, (card_name, position) in enumerate(cards, 1):
            tweet_data = mapping['cards'][card_name][position]

            # Screenshot
            screenshot_bytes = screenshot_tweet(page, tweet_data)
            screenshots[(card_name, position)] = screenshot_bytes

            # Progress
            print(f"  [{i}/{len(cards)}] {card_name} ({position})...")

        browser.close()

    print(f"✓ Generated {len(screenshots)} tweet screenshots")
    return screenshots
```

**Step 2: Update main() to test screenshots**

Add after loading mappings in main(), before the except block:
```python
        # Test screenshot generation
        if True:  # Change to False to skip during development
            screenshots = generate_tweet_screenshots(mapping)

            # Save one test screenshot
            test_key = ('The Fool', 'upright')
            if test_key in screenshots:
                test_path = '/tmp/test_tweet_screenshot.png'
                with open(test_path, 'wb') as f:
                    f.write(screenshots[test_key])
                print(f"\n✓ Test screenshot saved to {test_path}")
```

**Step 3: Install Playwright browser**

Run:
```bash
pip install playwright
playwright install chromium
```

**Step 4: Test screenshot generation**

Run:
```bash
cd /home/gabe/dril-tarot
python3 generate_dril_tarot_images.py
```

Expected: All 156 tweets screenshot successfully, test image saved

**Step 5: Commit**

```bash
git add generate_dril_tarot_images.py
git commit -m "feat: implement Playwright tweet screenshots

- Add screenshot_tweet() for single tweet
- Add generate_tweet_screenshots() for all 156 tweets
- Reuse single browser instance for efficiency
- Screenshot only .tweet-card element for clean output"
```

---

## Task 5: Download Public Domain Tarot Cards

**Files:**
- Modify: `generate_dril_tarot_images.py`
- Create: `tarot-cards/.gitkeep`

**Step 1: Add card download functions**

Add after generate_tweet_screenshots():
```python
import requests
from urllib.parse import quote


def sanitize_filename(name: str) -> str:
    """Convert card name to safe filename"""
    return name.lower().replace(' ', '-').replace('/', '-')


def download_rws_cards(output_dir: str) -> bool:
    """
    Download public domain Rider-Waite Smith tarot card images.

    Uses Wikimedia Commons public domain RWS deck.

    Args:
        output_dir: Directory to save card images

    Returns:
        True if successful, False otherwise
    """
    print("\nDownloading public domain RWS tarot cards...")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Wikimedia Commons RWS 1909 deck URLs
    # These are the original Pamela Colman Smith illustrations (public domain)
    base_url = "https://upload.wikimedia.org/wikipedia/commons/"

    # Major Arcana mappings (Wikipedia file names)
    major_arcana_files = {
        'The Fool': '9/90/RWS_Tarot_00_Fool.jpg',
        'The Magician': 'd/de/RWS_Tarot_01_Magician.jpg',
        'The High Priestess': '8/88/RWS_Tarot_02_High_Priestess.jpg',
        'The Empress': 'd/d2/RWS_Tarot_03_Empress.jpg',
        'The Emperor': 'c/c3/RWS_Tarot_04_Emperor.jpg',
        'The Hierophant': '8/8d/RWS_Tarot_05_Hierophant.jpg',
        'The Lovers': '3/3a/RWS_Tarot_06_Lovers.jpg',
        'The Chariot': '9/9b/RWS_Tarot_07_Chariot.jpg',
        'Strength': 'f/f5/RWS_Tarot_08_Strength.jpg',
        'The Hermit': '4/4d/RWS_Tarot_09_Hermit.jpg',
        'Wheel of Fortune': '3/3c/RWS_Tarot_10_Wheel_of_Fortune.jpg',
        'Justice': 'e/e0/RWS_Tarot_11_Justice.jpg',
        'The Hanged Man': '2/2b/RWS_Tarot_12_Hanged_Man.jpg',
        'Death': 'd/d7/RWS_Tarot_13_Death.jpg',
        'Temperance': 'f/f8/RWS_Tarot_14_Temperance.jpg',
        'The Devil': '5/55/RWS_Tarot_15_Devil.jpg',
        'The Tower': '5/53/RWS_Tarot_16_Tower.jpg',
        'The Star': 'd/db/RWS_Tarot_17_Star.jpg',
        'The Moon': '7/7f/RWS_Tarot_18_Moon.jpg',
        'The Sun': '1/17/RWS_Tarot_19_Sun.jpg',
        'Judgement': 'd/dd/RWS_Tarot_20_Judgement.jpg',
        'The World': 'f/ff/RWS_Tarot_21_World.jpg',
    }

    # Minor Arcana naming pattern
    suits = {
        'Wands': 'Wands',
        'Cups': 'Cups',
        'Swords': 'Swords',
        'Pentacles': 'Pentacles'
    }

    ranks = {
        'Ace': 'Ace',
        'Two': '02',
        'Three': '03',
        'Four': '04',
        'Five': '05',
        'Six': '06',
        'Seven': '07',
        'Eight': '08',
        'Nine': '09',
        'Ten': '10',
        'Page': 'Page',
        'Knight': 'Knight',
        'Queen': 'Queen',
        'King': 'King'
    }

    # Build minor arcana URLs
    minor_arcana_files = {}
    for suit_name, suit_wiki in suits.items():
        for rank_name, rank_wiki in ranks.items():
            card_name = f"{rank_name} of {suit_name}"
            # Wikipedia naming: RWS_Tarot_Wands01.jpg (for Ace of Wands)
            wiki_file = f"RWS_Tarot_{suit_wiki}{rank_wiki}.jpg"

            # Find the hash path (simplified - using common paths)
            # In reality, would need to query Wikipedia API or have full mapping
            # For now, construct likely path
            hash_prefix = wiki_file[0].lower()
            minor_arcana_files[card_name] = f"{hash_prefix}/{hash_prefix}{hash_prefix}/{wiki_file}"

    all_cards = {**major_arcana_files, **minor_arcana_files}

    # Download each card
    success_count = 0
    for card_name, url_path in all_cards.items():
        filename = sanitize_filename(card_name) + '.jpg'
        output_path = os.path.join(output_dir, filename)

        # Skip if exists
        if os.path.exists(output_path):
            success_count += 1
            continue

        url = base_url + url_path

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                f.write(response.content)

            print(f"  ✓ {card_name}")
            success_count += 1

        except Exception as e:
            print(f"  ✗ {card_name}: {e}")

    print(f"\n✓ Downloaded {success_count}/{len(all_cards)} cards")

    if success_count < 78:
        print("\n⚠️  Some cards failed to download.")
        print("Manual download instructions:")
        print("  1. Visit: https://en.wikipedia.org/wiki/Rider-Waite_tarot_deck")
        print("  2. Download missing card images")
        print(f"  3. Save to: {output_dir}/")
        print("  4. Use naming: the-fool.jpg, ace-of-wands.jpg, etc.")
        return False

    return True


def verify_card_images(cards_dir: str) -> Tuple[bool, List[str]]:
    """
    Verify all 78 tarot card images are present.

    Returns:
        (success, missing_cards)
    """
    # Load card names from mapping
    with open(CARD_MAPPING_FILE, 'r') as f:
        mapping = json.load(f)

    card_names = list(mapping['cards'].keys())
    missing = []

    for card_name in card_names:
        filename = sanitize_filename(card_name) + '.jpg'
        path = os.path.join(cards_dir, filename)

        if not os.path.exists(path):
            missing.append(card_name)

    return len(missing) == 0, missing
```

**Step 2: Update main() to handle card download**

Replace the test screenshot code in main() with:
```python
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
```

**Step 3: Test card download**

Run:
```bash
cd /home/gabe/dril-tarot
python3 generate_dril_tarot_images.py --download-cards
```

Expected: 78 cards downloaded (or error with manual instructions)

**Step 4: Commit**

```bash
mkdir -p tarot-cards
touch tarot-cards/.gitkeep
git add generate_dril_tarot_images.py tarot-cards/.gitkeep
git commit -m "feat: add RWS tarot card download

- Download public domain RWS cards from Wikimedia
- Verify all 78 cards present before proceeding
- Provide manual download instructions on failure
- Sanitize card names to safe filenames"
```

---

## Task 6: Implement Image Composition

**Files:**
- Modify: `generate_dril_tarot_images.py`

**Step 1: Add composition function**

Add after verify_card_images():
```python
from io import BytesIO


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

    # Paste tweet onto card (opaque)
    card.paste(tweet_img, (x, y))

    return card


def generate_gallery_images(
    mapping: Dict,
    cards_dir: str,
    output_dir: str,
    skip_existing: bool = False
):
    """
    Generate all 156 gallery images.

    Args:
        mapping: Card mapping data
        cards_dir: Directory with tarot card images
        output_dir: Output directory for gallery
        skip_existing: Skip if output file exists
    """
    print("\nGenerating gallery images...")
    print("=" * 70)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Generate tweet screenshots
    screenshots = generate_tweet_screenshots(mapping)

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

        # Get card image path
        card_image_filename = sanitize_filename(card_name) + '.jpg'
        card_image_path = os.path.join(cards_dir, card_image_filename)

        # Get tweet screenshot
        screenshot_bytes = screenshots[(card_name, position)]

        # Composite
        composite = composite_tweet_on_card(
            card_image_path,
            screenshot_bytes,
            card_name,
            position
        )

        # Save
        composite.save(output_path, 'PNG', quality=95)

        print(f"[{i}/{len(cards)}] {card_name} ({position}) → {output_filename}")

    print("\n" + "=" * 70)
    print(f"✓ Generated {len(cards)} gallery images in {output_dir}/")
```

**Step 2: Update main() to call generation**

Replace the verification code in main() (keep the verification part, add after it):
```python
        # Generate gallery
        generate_gallery_images(
            mapping,
            args.card_images_dir,
            args.output,
            args.skip_existing
        )

        print("\n" + "=" * 70)
        print("Gallery generation complete!")
        print(f"Images saved to: {args.output}/")
        print("=" * 70)
```

**Step 3: Test full generation**

Run:
```bash
cd /home/gabe/dril-tarot
python3 generate_dril_tarot_images.py
```

Expected: All 156 images generated in gallery/ directory

**Step 4: Verify a few outputs**

Run:
```bash
ls -lh gallery/ | head -10
file gallery/the-fool-upright.png
```

Expected: PNG files, reasonable sizes

**Step 5: Commit**

```bash
git add generate_dril_tarot_images.py
git commit -m "feat: implement image composition

- Composite tweet screenshots onto tarot cards
- Center tweets on cards (horizontal and vertical)
- Rotate cards 180° for reversed positions
- Generate all 156 gallery images
- Support --skip-existing for resumable generation"
```

---

## Task 7: Error Handling and Polish

**Files:**
- Modify: `generate_dril_tarot_images.py`

**Step 1: Add better error handling**

Wrap the generate_tweet_screenshots() function with try-except:
```python
def generate_tweet_screenshots(mapping: Dict) -> Dict[Tuple[str, str], bytes]:
    """
    Generate all tweet screenshots using Playwright.

    Args:
        mapping: Card mapping data

    Returns:
        Dict mapping (card_name, position) -> screenshot PNG bytes
    """
    screenshots = {}

    print("\nGenerating tweet screenshots...")

    try:
        with sync_playwright() as p:
            # Launch browser (headless)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 600, 'height': 800})

            # Process each card
            cards = get_card_processing_order(mapping)
            for i, (card_name, position) in enumerate(cards, 1):
                tweet_data = mapping['cards'][card_name][position]

                try:
                    # Screenshot
                    screenshot_bytes = screenshot_tweet(page, tweet_data)
                    screenshots[(card_name, position)] = screenshot_bytes

                    # Progress
                    if i % 10 == 0:  # Show progress every 10
                        print(f"  Progress: {i}/{len(cards)} tweets...")
                except Exception as e:
                    print(f"  ✗ Failed {card_name} ({position}): {e}")
                    # Continue with others

            browser.close()
    except Exception as e:
        print(f"\n✗ Playwright error: {e}")
        print("Make sure Playwright is installed: playwright install chromium")
        raise

    print(f"✓ Generated {len(screenshots)} tweet screenshots")
    return screenshots
```

**Step 2: Add Playwright check at startup**

Add before main():
```python
def check_playwright_installed():
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
```

Add to main() after loading mapping:
```python
        # Check Playwright
        if not check_playwright_installed():
            print("\n✗ Playwright not installed or browsers not available")
            print("Install with: playwright install chromium")
            sys.exit(1)
```

**Step 3: Add .gitignore for gallery**

Create `.gitignore` entry (or edit existing):
```bash
echo "gallery/" >> .gitignore
echo "tarot-cards/*.jpg" >> .gitignore
```

**Step 4: Test error handling**

Test with missing Playwright:
```bash
# Temporarily rename browser to test error
# (skip if you don't want to break your setup)
```

**Step 5: Commit**

```bash
git add generate_dril_tarot_images.py .gitignore
git commit -m "feat: add error handling and polish

- Check Playwright installed before starting
- Continue generation if single tweet fails
- Show progress every 10 screenshots
- Add gallery/ and downloaded cards to .gitignore"
```

---

## Task 8: Documentation and Final Testing

**Files:**
- Modify: `README.md`
- Create: `gallery/.gitkeep`

**Step 1: Update README with gallery instructions**

Add to README.md after "Generate Tweet Matches" section:
```markdown
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
```

**Step 2: Add gallery examples to README**

Add example matches section:
```markdown
## Gallery Examples

Once generated, you'll have beautiful composite images like:
- The Fool (upright) + "inventing a new Suit of playing cards..."
- Death (reversed) + "❒Single ❒Taken GenderDead"
- The Tower (reversed) + "betrayed my 'NO FEAR' tower decal"
```

**Step 3: Full end-to-end test**

Run complete workflow:
```bash
cd /home/gabe/dril-tarot

# Clean slate
rm -rf gallery/ tarot-cards/

# Full generation
python3 generate_dril_tarot_images.py --download-cards

# Verify output
ls gallery/ | wc -l  # Should be 156
file gallery/the-fool-upright.png  # Should be PNG
```

Expected: 156 images successfully generated

**Step 4: Create gallery .gitkeep**

```bash
mkdir -p gallery
touch gallery/.gitkeep
```

**Step 5: Final commit**

```bash
git add README.md gallery/.gitkeep
git commit -m "docs: add gallery generation instructions

- Update README with generation commands
- Add gallery examples
- Document output format and structure"
```

---

## Task 9: Optimize and Performance Improvements (Optional)

**Files:**
- Modify: `generate_dril_tarot_images.py`

**Step 1: Add caching for tweet screenshots**

Optional: Cache screenshots to disk to speed up re-runs:
```python
TWEET_SCREENSHOTS_CACHE = 'data/tweet_screenshots_cache.json'

def cache_screenshots(screenshots: Dict[Tuple[str, str], bytes]):
    """Cache tweet screenshots to disk"""
    # Convert to serializable format
    cache_data = {}
    for (card_name, position), screenshot_bytes in screenshots.items():
        import base64
        key = f"{card_name}|{position}"
        cache_data[key] = base64.b64encode(screenshot_bytes).decode('utf-8')

    with open(TWEET_SCREENSHOTS_CACHE, 'w') as f:
        json.dump(cache_data, f)

def load_cached_screenshots() -> Dict[Tuple[str, str], bytes]:
    """Load cached screenshots"""
    if not os.path.exists(TWEET_SCREENSHOTS_CACHE):
        return None

    try:
        with open(TWEET_SCREENSHOTS_CACHE, 'r') as f:
            cache_data = json.load(f)

        import base64
        screenshots = {}
        for key, b64_data in cache_data.items():
            card_name, position = key.split('|')
            screenshots[(card_name, position)] = base64.b64decode(b64_data)

        return screenshots
    except:
        return None
```

**Step 2: Add --regenerate-screenshots flag**

Add to argparse:
```python
parser.add_argument(
    '--regenerate-screenshots',
    action='store_true',
    help='Force regenerate tweet screenshots (ignore cache)'
)
```

**Step 3: Commit optimization**

```bash
git add generate_dril_tarot_images.py
git commit -m "feat: add screenshot caching for faster re-runs

- Cache tweet screenshots to data/tweet_screenshots_cache.json
- Add --regenerate-screenshots flag to force regeneration
- Speeds up re-runs when only card images change"
```

---

## Completion Checklist

- [ ] All tasks completed
- [ ] All 156 images generate successfully
- [ ] Error handling works (tested with missing files)
- [ ] Documentation updated
- [ ] All commits pushed
- [ ] Gallery images look good (manual QA check)

## Notes

- The Wikimedia URLs in Task 5 are approximate. The actual download implementation may need adjustment based on Wikipedia's file structure
- If Wikimedia download fails, provide manual download instructions
- Tweet HTML styling is based on classic Twitter design circa 2018
- Images are high-resolution (1200px tall) suitable for web display and printing
