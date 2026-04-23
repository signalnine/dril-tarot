# CONTRACT: Preserve tweet-card rounded corners in gallery composite

Tracks bd issue `dril-tarot-892`.

## Problem

`composite_tweet_on_card()` calls `card.paste(tweet_img, (x, y))` with an RGBA
tweet screenshot and an RGB card. Without a mask, PIL copies the source RGB
values and drops the alpha channel, so transparent pixels around the tweet
card's `border-radius` corners (alpha=0) get pasted as solid RGB. The result
is a visible rectangular patch painted over the tarot card exactly where the
rounded corners should let the card show through.

## Behaviors required

- [x] When the tweet screenshot has transparent pixels (RGBA), those pixels
      must not overwrite the tarot card beneath; the card's colors must remain
      visible in those positions.
- [x] When the tweet screenshot has opaque pixels, they continue to replace
      the card beneath unchanged (the tweet body still appears over the card).
- [x] Non-RGBA tweet screenshots (e.g. RGB PNG without alpha) continue to
      composite correctly without regression.

## Verification

- [x] New test `tests/test_transparent_composite.py` builds an RGBA tweet image
      with a distinct colored border-radius corner region (alpha=0), composites
      it onto a uniformly colored RGB card via `composite_tweet_on_card`, and
      asserts:
      - a pixel inside a transparent corner retains the card's color,
      - a pixel inside the opaque tweet body matches the tweet body color,
      - no exception is raised.
- [x] Test fails on current `main` (transparent corner pixel equals the tweet
      RGB value rather than the card color).
- [x] Test passes after fix.
- [x] Pre-existing `tests/test_missing_screenshot.py` still passes.
