# Dril-Tarot Gallery Image Generator - Design Document

**Date:** 2025-12-12
**Status:** Approved

## Overview

A script that generates 156 composite images combining public domain Rider-Waite Smith tarot cards with styled dril tweet mockups, creating a browseable gallery of all dril-tarot matches.

## Architecture

### Core Components

**generate_dril_tarot_images.py** - Main script that:
1. Loads `card_dril_mapping.json` to get all card-tweet pairs
2. Fetches/verifies 78 Rider-Waite Smith tarot card images (public domain)
3. Generates tweet mockups using Playwright (HTML/CSS → screenshot)
4. Composites tweet screenshots onto tarot card images using Pillow
5. Saves 156 PNG files to `gallery/` directory

**Tech Stack:**
- `playwright` - Headless Chromium for screenshotting HTML/CSS tweet mockups
- `Pillow (PIL)` - Image manipulation and compositing
- `requests` - Download public domain tarot card images
- Existing: `card_dril_mapping.json` for matches

**Output:**
- 156 PNG files: `gallery/the-fool-upright.png` through `gallery/king-of-pentacles-reversed.png`
- Each image: RWS tarot card with classic Twitter-styled tweet centered on top
- High resolution for web display and potential printing

## Tweet Mockup Generation

### HTML/CSS Template

Classic Twitter appearance:
- **Header**: "dril" name, @dril handle, placeholder profile picture
- **Tweet body**: Tweet text in Helvetica/Arial
- **Footer**: Engagement metrics (retweet count, like count from mapping)
- **Timestamp**: Tweet date
- **Styling**: White background, Twitter blue (#1DA1F2) accents, proper padding

### Playwright Screenshot Process

1. Generate HTML string for each tweet using template
2. Launch headless Chromium browser (reuse single instance for all 156 tweets)
3. Create page, set viewport to fixed size (600x400px)
4. Load HTML content
5. Screenshot to PNG in memory
6. Process all tweets, then close browser

### Text Handling

- CSS `word-wrap` for proper line breaking
- Handle special characters, emojis, line breaks
- Consistent sizing via CSS (no manual text measurement needed)

## Tarot Card Image Sourcing

### Public Domain RWS Images

Source from:
- Sacred Texts (sacred-texts.com) - public domain RWS scans
- Wikimedia Commons - public domain tarot collections
- Or user provides their own directory

### Image Requirements

- 78 unique cards
- For reversed positions: programmatically rotate upright images 180°
- Consistent resolution (script will resize/standardize)
- File naming that maps to `card_dril_mapping.json` card names

### Script Approach

- `--download-cards` flag: automatically fetch RWS images from public domain source
- `--card-images-dir` flag: use existing card image directory
- Validation: ensure all 78 cards present before generating
- Handle reversed by rotating upright images (simpler than 156 pre-made files)

### Fallback

If download fails, provide clear instructions with links to public domain sources for manual download.

## Image Composition

### Compositing with Pillow

Process for each card:
1. Load base tarot card image (PNG/JPG)
2. Resize/standardize to consistent dimensions (e.g., 600x1000px)
3. Load tweet screenshot PNG
4. Calculate center position (both horizontal and vertical)
5. Paste tweet onto card (opaque overlay, no transparency)
6. Save composite as high-quality PNG

### Layout Specifics

- Tweet mockup: ~500px wide, height varies by tweet length
- Positioned dead center on card
- Tweet has opaque white background (obscures card art beneath)
- Output format: PNG (lossless)
- Resolution: Keep original or upscale to ~1200px tall for quality
- Color space: RGB

### Edge Cases

- Very long tweets: ensure mockup fits on card or truncate
- Variable card aspect ratios: handle different source dimensions

## File Naming & Organization

### Output Structure

```
gallery/
├── the-fool-upright.png
├── the-fool-reversed.png
├── the-magician-upright.png
├── the-magician-reversed.png
├── ...
├── king-of-pentacles-upright.png
└── king-of-pentacles-reversed.png
```

### Naming Convention

- Lowercase card names with hyphens: `the-fool`, `ace-of-wands`
- Position suffix: `-upright` or `-reversed`
- Extension: `.png`

### Generation Order

- Process in order: Major Arcana first, then Minor Arcana by suit
- Progress indicator showing current card
- `--skip-existing` flag to resume interrupted runs

### Console Output

```
Generating dril-tarot gallery images...
✓ Verified 78 tarot card images
✓ Playwright browser ready

[1/156] The Fool (upright)... ✓
[2/156] The Fool (reversed)... ✓
[3/156] The Magician (upright)... ✓
...
[156/156] King of Pentacles (reversed)... ✓

✓ Generated 156 images in gallery/
```

## Command-line Interface

### Usage

```bash
# Download cards and generate all images
python3 generate_dril_tarot_images.py --download-cards

# Use existing card images
python3 generate_dril_tarot_images.py --card-images-dir ./my-tarot-cards

# Resume interrupted generation
python3 generate_dril_tarot_images.py --skip-existing

# Specify output directory
python3 generate_dril_tarot_images.py --output gallery-v2
```

### Command-line Flags

- `--download-cards` - Auto-download public domain RWS images
- `--card-images-dir PATH` - Use existing card image directory
- `--output DIR` - Output directory (default: `gallery/`)
- `--skip-existing` - Don't regenerate existing images
- `--system SYSTEM` - Use specific interpretation system's mapping (default: uses existing `card_dril_mapping.json`)

## Error Handling

- **Missing card_dril_mapping.json** → Clear error: "Run match_dril_tweets.py first"
- **Card images not found** → Suggest `--download-cards` or provide manual download instructions
- **Playwright not installed** → Instructions: `pip install playwright && playwright install chromium`
- **Failed screenshot** → Log error, continue with remaining cards
- **Disk space issues** → Check available space before starting

## Dependencies

Add to `requirements.txt`:
- `playwright` - Headless browser automation

Already available:
- `Pillow` - Image manipulation (used by other scripts)
- `requests` - HTTP client

## Implementation Notes

### Tweet Template HTML Example

```html
<div class="tweet-card">
  <div class="tweet-header">
    <img class="avatar" src="data:image/..." />
    <div class="user-info">
      <span class="name">dril</span>
      <span class="handle">@dril</span>
    </div>
  </div>
  <div class="tweet-body">
    {tweet_content}
  </div>
  <div class="tweet-footer">
    <span class="timestamp">{date}</span>
    <span class="engagement">🔁 {retweets} ❤️ {favorites}</span>
  </div>
</div>
```

### Card Name Mapping

Convert card names from `card_dril_mapping.json` to filesystem-safe names:
- "The Fool" → "the-fool"
- "Ace of Wands" → "ace-of-wands"
- "King of Pentacles" → "king-of-pentacles"

### Performance Considerations

- Single Playwright browser instance for all 156 tweets (~2-3 minutes total)
- Batch processing with progress updates
- Image caching to avoid re-downloading cards
- `--skip-existing` for resumable generation

## Future Enhancements

Once basic generation works:
- HTML gallery page with thumbnails and navigation
- Different tweet styles (dark mode, minimal, etc.)
- Configurable tweet positioning (top, bottom, centered)
- Export different resolutions (web, print, social media)
- Animated GIFs showing card flip with tweet reveal
