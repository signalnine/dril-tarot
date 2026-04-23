# CONTRACT: Flatten palette-mode PNG transparency onto white in avatar encoder

Tracks bd issue `dril-tarot-7hr`.

## Problem

`utils/download_dril_avatar.py::image_to_base64` resizes the source image,
then flattens `RGBA`/`LA` inputs onto a white background before JPEG encoding.
Every other mode falls through to a bare `Image.convert('RGB')`. Palette-mode
(`P`) PNGs whose transparency is declared via the `transparency` info key
carry no alpha channel, so a direct RGB conversion paints transparent pixels
with whatever palette color sits at the transparent index. The resulting
avatar has stray color smears where the source intended transparency.

The sibling downloader `download_tarot_cards.py` already handles this case
correctly by routing `P` through `RGBA` first -- the two files diverged.

## Behaviors required

- [x] Palette-mode PNG with a declared transparent index is flattened onto
      the white background, matching the RGBA/LA behavior.
- [x] Opaque palette pixels still render as their palette RGB after encoding.
- [x] Pre-existing RGBA and LA handling continues to work without regression.
- [x] Plain RGB inputs are unaffected.

## Verification

- [x] `tests/test_avatar_base64.py::test_p_mode_transparent_region_becomes_white`
      builds a 48x48 P-mode PNG whose left half uses a transparent palette
      index and asserts the center of that half encodes to near-white after
      a round-trip through `image_to_base64`.
- [x] `test_p_mode_opaque_region_is_preserved` asserts the opaque right half
      still renders as the palette red.
- [x] `test_rgba_transparent_region_still_flattens_onto_white` locks in the
      pre-existing RGBA code path.
- [x] Failing-test run on unfixed code showed `(0, 255, 1)` at the transparent
      sample point (palette green bleed-through); fixed run returns near-white.
- [x] Pre-existing `tests/test_missing_screenshot.py` and
      `tests/test_transparent_composite.py` still pass.
