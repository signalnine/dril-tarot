#!/usr/bin/env python3
"""
Helper script to download dril's profile picture and convert to base64.

This script helps you get dril's current profile picture from Twitter/X
and convert it to base64 for embedding in the tweet HTML template.
"""

import base64
import sys
from pathlib import Path

def image_to_base64(image_path: str) -> str:
    """Convert image file to base64 data URI."""
    from PIL import Image
    from io import BytesIO

    # Load and resize image to 48x48 (avatar size)
    img = Image.open(image_path)
    img = img.resize((48, 48), Image.Resampling.LANCZOS)

    # Flatten any transparency onto a white background before writing JPEG.
    # Palette ('P') PNGs carry transparency via the info['transparency'] key
    # rather than a dedicated alpha channel; converting straight to RGB
    # would paint the transparent index with its palette color instead of
    # letting the background show through, so route P through RGBA first.
    if img.mode in ('RGBA', 'LA', 'P'):
        if img.mode == 'P':
            img = img.convert('RGBA')
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Save to bytes
    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=95)
    img_bytes = buffer.getvalue()

    # Convert to base64
    b64 = base64.b64encode(img_bytes).decode('utf-8')

    # Return as data URI
    return f"data:image/jpeg;base64,{b64}"


def main() -> None:
    print("Dril Avatar Base64 Converter")
    print("=" * 70)
    print()
    print("To get dril's profile picture:")
    print("  1. Visit https://twitter.com/dril")
    print("  2. Right-click on the profile picture")
    print("  3. Save image as 'dril_avatar.jpg' in this directory")
    print()
    print("Or download directly from:")
    print("  https://pbs.twimg.com/profile_images/[current-id]/[filename]")
    print()
    print("=" * 70)
    print()

    if len(sys.argv) > 1:
        avatar_path = sys.argv[1]
    else:
        avatar_path = input("Enter path to dril avatar image: ").strip()

    if not Path(avatar_path).exists():
        print(f"Error: File not found: {avatar_path}")
        sys.exit(1)

    try:
        base64_uri = image_to_base64(avatar_path)

        print("\n✓ Image converted to base64!")
        print(f"  Original: {avatar_path}")
        print(f"  Size: {len(base64_uri)} characters")
        print()
        print("Copy this line to replace the avatar_placeholder in generate_dril_tarot_images.py:")
        print()
        print(f'avatar_placeholder = "{base64_uri}"')
        print()

        # Also save to file
        output_file = Path(__file__).parent.parent / 'data' / 'dril_avatar_base64.txt'
        output_file.parent.mkdir(exist_ok=True)
        output_file.write_text(base64_uri)

        print(f"Also saved to: {output_file}")

    except Exception as e:
        print(f"Error converting image: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
