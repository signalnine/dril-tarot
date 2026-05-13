# CONTRACT: direct tests for composite_tweet_on_card guard rails

Tracks bd issue `dril-tarot-yk5`.

## Problem

`composite_tweet_on_card` (generate_dril_tarot_images.py:482) has explicit
guard rails and a reversed-rotation branch that are only exercised
indirectly via `test_gallery_composite_resilience` and
`test_transparent_composite`. The guard branches themselves have no
direct coverage:

- `card.width == 0 or card.height == 0` -> `ValueError('Invalid card image dimensions')`
- `card.width > 10000 or card.height > 10000` -> `ValueError('Card image too large')`
- `position == 'reversed'` -> output is rotated 180 degrees

## Behaviors required

- [x] A zero-pixel card image makes `composite_tweet_on_card` raise
      `ValueError` with a message that mentions "Invalid card image
      dimensions".
- [x] An oversize card image (width or height > 10000) makes
      `composite_tweet_on_card` raise `ValueError` with a message that
      mentions "Card image too large".
- [x] When `position='reversed'`, the rendered card is rotated 180
      degrees relative to the same render with `position='upright'`.
      Verified by placing a known marker (a colored stripe across the
      top of the card) and asserting it appears at the bottom of the
      reversed output.
- [x] Pre-existing tests in `tests/` continue to pass.

## Verification

- [x] New test file `tests/test_composite_guards.py` exists with one
      pytest per behavior above.
- [x] Uses the same `sys.path.insert` import pattern as the rest of
      `tests/`.
- [x] `python3 -m pytest tests/` reports all tests passing
      (51 total: 48 existing + 3 new).
- [x] Mutation-tested: each test fails when its corresponding guard or
      the `rotate(180)` call is removed, confirming the tests actually
      exercise those branches rather than passing incidentally.
