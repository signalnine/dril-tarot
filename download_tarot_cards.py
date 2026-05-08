#!/usr/bin/env python3
"""
Helper script to download public domain Rider-Waite Smith tarot cards
from Internet Archive.

This script downloads the 1909 Pamela Colman Smith illustrations,
which are in the public domain.
"""

import os
import sys
import requests
from pathlib import Path

# Internet Archive direct download URLs for RWS deck
# These are stable URLs from the rider-waite-tarot collection
BASE_URL = "https://archive.org/download/rider-waite-tarot/"

# Card mapping to Internet Archive filenames
# Based on actual filenames in the rider-waite-tarot archive
CARD_URLS = {
    # Major Arcana (0-21)
    'The Fool': 'major_arcana_fool.png',
    'The Magician': 'major_arcana_magician.png',
    'The High Priestess': 'major_arcana_priestess.png',
    'The Empress': 'major_arcana_empress.png',
    'The Emperor': 'major_arcana_emperor.png',
    'The Hierophant': 'major_arcana_hierophant.png',
    'The Lovers': 'major_arcana_lovers.png',
    'The Chariot': 'major_arcana_chariot.png',
    'Strength': 'major_arcana_strength.png',
    'The Hermit': 'major_arcana_hermit.png',
    'Wheel of Fortune': 'major_arcana_fortune.png',
    'Justice': 'major_arcana_justice.png',
    'The Hanged Man': 'major_arcana_hanged.png',
    'Death': 'major_arcana_death.png',
    'Temperance': 'major_arcana_temperance.png',
    'The Devil': 'major_arcana_devil.png',
    'The Tower': 'major_arcana_tower.png',
    'The Star': 'major_arcana_star.png',
    'The Moon': 'major_arcana_moon.png',
    'The Sun': 'major_arcana_sun.png',
    'Judgement': 'major_arcana_judgement.png',
    'The World': 'major_arcana_world.png',

    # Minor Arcana - Wands
    'Ace of Wands': 'minor_arcana_wands_ace.png',
    'Two of Wands': 'minor_arcana_wands_2.png',
    'Three of Wands': 'minor_arcana_wands_3.png',
    'Four of Wands': 'minor_arcana_wands_4.png',
    'Five of Wands': 'minor_arcana_wands_5.png',
    'Six of Wands': 'minor_arcana_wands_6.png',
    'Seven of Wands': 'minor_arcana_wands_7.png',
    'Eight of Wands': 'minor_arcana_wands_8.png',
    'Nine of Wands': 'minor_arcana_wands_9.png',
    'Ten of Wands': 'minor_arcana_wands_10.png',
    'Page of Wands': 'minor_arcana_wands_page.png',
    'Knight of Wands': 'minor_arcana_wands_knight.png',
    'Queen of Wands': 'minor_arcana_wands_queen.png',
    'King of Wands': 'minor_arcana_wands_king.png',

    # Minor Arcana - Cups
    'Ace of Cups': 'minor_arcana_cups_ace.png',
    'Two of Cups': 'minor_arcana_cups_2.png',
    'Three of Cups': 'minor_arcana_cups_3.png',
    'Four of Cups': 'minor_arcana_cups_4.png',
    'Five of Cups': 'minor_arcana_cups_5.png',
    'Six of Cups': 'minor_arcana_cups_6.png',
    'Seven of Cups': 'minor_arcana_cups_7.png',
    'Eight of Cups': 'minor_arcana_cups_8.png',
    'Nine of Cups': 'minor_arcana_cups_9.png',
    'Ten of Cups': 'minor_arcana_cups_10.png',
    'Page of Cups': 'minor_arcana_cups_page.png',
    'Knight of Cups': 'minor_arcana_cups_knight.png',
    'Queen of Cups': 'minor_arcana_cups_queen.png',
    'King of Cups': 'minor_arcana_cups_king.png',

    # Minor Arcana - Swords
    'Ace of Swords': 'minor_arcana_swords_ace.png',
    'Two of Swords': 'minor_arcana_swords_2.png',
    'Three of Swords': 'minor_arcana_swords_3.png',
    'Four of Swords': 'minor_arcana_swords_4.png',
    'Five of Swords': 'minor_arcana_swords_5.png',
    'Six of Swords': 'minor_arcana_swords_6.png',
    'Seven of Swords': 'minor_arcana_swords_7.png',
    'Eight of Swords': 'minor_arcana_swords_8.png',
    'Nine of Swords': 'minor_arcana_swords_9.png',
    'Ten of Swords': 'minor_arcana_swords_10.png',
    'Page of Swords': 'minor_arcana_swords_page.png',
    'Knight of Swords': 'minor_arcana_swords_knight.png',
    'Queen of Swords': 'minor_arcana_swords_queen.png',
    'King of Swords': 'minor_arcana_swords_king.png',

    # Minor Arcana - Pentacles
    'Ace of Pentacles': 'minor_arcana_pentacles_ace.png',
    'Two of Pentacles': 'minor_arcana_pentacles_2.png',
    'Three of Pentacles': 'minor_arcana_pentacles_3.png',
    'Four of Pentacles': 'minor_arcana_pentacles_4.png',
    'Five of Pentacles': 'minor_arcana_pentacles_5.png',
    'Six of Pentacles': 'minor_arcana_pentacles_6.png',
    'Seven of Pentacles': 'minor_arcana_pentacles_7.png',
    'Eight of Pentacles': 'minor_arcana_pentacles_8.png',
    'Nine of Pentacles': 'minor_arcana_pentacles_9.png',
    'Ten of Pentacles': 'minor_arcana_pentacles_10.png',
    'Page of Pentacles': 'minor_arcana_pentacles_page.png',
    'Knight of Pentacles': 'minor_arcana_pentacles_knight.png',
    'Queen of Pentacles': 'minor_arcana_pentacles_queen.png',
    'King of Pentacles': 'minor_arcana_pentacles_king.png',
}


def is_valid_cached_jpeg(path: str) -> bool:
    """Check that a cached card JPG is a complete, decodable image.

    A previous run killed mid-Image.save() leaves a 0-byte or truncated
    file behind. PIL's lazy loading lets Image.open() succeed on those,
    so we round-trip through Image.verify() which forces a decode pass.
    """
    try:
        if os.path.getsize(path) == 0:
            return False
    except OSError:
        return False
    try:
        from PIL import Image
        # verify() catches malformed headers but does NOT detect truncation
        # because PIL is lazy. After verify() the file handle is consumed,
        # so reopen and load() to force a full decode of the pixel data.
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            img.load()
        return True
    except Exception:
        return False


def sanitize_filename(name: str) -> str:
    """Convert card name to safe filename."""
    # Remove null bytes
    name = name.replace('\0', '')
    # Replace dangerous characters
    sanitized = name.lower().replace(' ', '-').replace('/', '-')
    # Remove leading/trailing dots and path separators
    sanitized = sanitized.strip('.-_')
    # Prevent directory traversal
    sanitized = sanitized.replace('..', '')
    # Limit length
    return sanitized[:255]


def download_cards(output_dir: str = 'tarot-cards') -> bool:
    """Download all 78 tarot cards from Internet Archive."""

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    print("Downloading Rider-Waite Smith Tarot Cards")
    print("Source: Internet Archive (Public Domain)")
    print("=" * 70)
    print()

    success_count = 0
    failed = []

    # Request headers to avoid issues
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; TarotDownloader/1.0)'
    }

    for card_name, archive_filename in CARD_URLS.items():
        # Output filename (convert PNG to JPG for consistency)
        output_filename = sanitize_filename(card_name) + '.jpg'
        output_path = os.path.join(output_dir, output_filename)

        # Skip if a valid cached JPG already exists. Validate before
        # short-circuiting so a 0-byte or truncated file from a killed
        # earlier run doesn't masquerade as a successful cache hit.
        if os.path.exists(output_path):
            if is_valid_cached_jpeg(output_path):
                print(f"  ✓ {card_name:30} (cached)")
                success_count += 1
                continue
            print(f"  ! {card_name:30} (corrupt cache, redownloading)")
            try:
                os.remove(output_path)
            except OSError as e:
                print(f"  ✗ {card_name:30} (could not remove corrupt file: {e})")
                failed.append((card_name, archive_filename, f"corrupt cache: {e}"))
                continue

        # Download URL
        url = BASE_URL + archive_filename

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            # Convert PNG to JPG for consistency with the rest of the pipeline
            from PIL import Image
            from io import BytesIO

            img = Image.open(BytesIO(response.content))
            # Convert to RGB if necessary (PNG might have alpha channel)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                # Get alpha channel
                if img.mode in ('RGBA', 'LA'):
                    alpha = img.split()[-1]
                    background.paste(img, mask=alpha)
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Save as JPG
            img.save(output_path, 'JPEG', quality=95)

            print(f"  ✓ {card_name:30} → {output_filename}")
            success_count += 1

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"  ✗ {card_name:30} (not found)")
                failed.append((card_name, archive_filename, "404 Not Found"))
            else:
                print(f"  ✗ {card_name:30} ({e})")
                failed.append((card_name, archive_filename, str(e)))
        except Exception as e:
            print(f"  ✗ {card_name:30} ({e})")
            failed.append((card_name, archive_filename, str(e)))

    print()
    print("=" * 70)
    print(f"Downloaded: {success_count}/{len(CARD_URLS)} cards")

    if failed:
        print(f"\nFailed: {len(failed)} cards")
        print("\nYou can manually download these from:")
        print("https://archive.org/details/rider-waite-tarot")
        print("\nOr try alternative sources:")
        print("- https://luciellaes.itch.io/rider-waite-smith-tarot-cards-cc0")
        print("- https://sacred-texts.com/tarot/pkt/index.htm")
        print()
        print("Save them to:", os.path.abspath(output_dir))
        print("\nFailed cards:")
        for card_name, archive_name, error in failed[:10]:
            output_name = sanitize_filename(card_name) + '.jpg'
            print(f"  - {card_name} → {output_name}")
        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more")
        return False

    print(f"\n✓ All cards downloaded to: {os.path.abspath(output_dir)}/")
    print("\nYou can now run:")
    print("  python3 generate_dril_tarot_images.py --card-images-dir", output_dir)

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Download public domain RWS tarot cards from Internet Archive'
    )
    parser.add_argument(
        '--output',
        default='tarot-cards',
        help='Output directory (default: tarot-cards)'
    )

    args = parser.parse_args()

    success = download_cards(args.output)
    sys.exit(0 if success else 1)
