# CONTRACT: Missing-screenshot resilience in gallery generation

Tracks bd issue `dril-tarot-qnk`.

## Problem

`generate_tweet_screenshots()` catches per-card exceptions and prints a warning, but leaves the `(card_name, position)` key absent from the returned dict. Its consumer `generate_gallery_images()` then does `screenshots[(card_name, position)]` without a guard, so one failed screenshot raises `KeyError` and aborts the whole gallery run. Same hazard applies to a partially-populated cached screenshots file loaded by `load_cached_screenshots()`.

## Behaviors required

- [x] When a `(card_name, position)` has no entry in the `screenshots` dict, `generate_gallery_images()` logs a warning to stderr identifying the card and position, and skips that gallery image.
- [x] After skipping a missing screenshot, `generate_gallery_images()` continues processing the remaining cards.
- [x] When all screenshots are present, behavior is unchanged: all images are generated.

## Verification

- [x] New test `tests/test_missing_screenshot.py` invokes `generate_gallery_images` with a screenshots dict that intentionally omits one key, and asserts:
  - no exception is raised,
  - the remaining card still reaches the save path,
  - a warning mentioning the missing card+position is printed to stderr.
- [x] Test fails on current `main` (confirmed: `KeyError: ('The Fool', 'upright')`).
- [x] Test passes after fix.
- [x] Existing scripts still import cleanly (`python3 -c "import generate_dril_tarot_images"`).
