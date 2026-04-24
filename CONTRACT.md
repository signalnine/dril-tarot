# CONTRACT: Harden load_tweet_embeddings against corrupt cache

Tracks bd issue `dril-tarot-6a4`.

## Problem

`match_dril_tweets.py::load_tweet_embeddings` assumes the cache file is
always well-formed. If `data/dril_tweet_embeddings.json` is truncated,
invalid JSON, or missing the top-level `embeddings` key, the helper raises
`json.JSONDecodeError`, `KeyError`, or `OSError`; none are caught, so the
entire script aborts with a traceback from `main`'s generic handler. The
cache is ~370MB, and corruption is plausible (killed write, disk full,
partial download). The sibling helper `load_cached_screenshots` in
`generate_dril_tarot_images.py` already handles this case by warning and
returning `None`, which lets the caller fall back to regeneration.
`load_tweet_embeddings` must behave the same way.

## Behaviors required

- [x] Non-existent cache file: `load_tweet_embeddings()` returns `None`
      (pre-existing behavior, must not regress).
- [x] Cache file containing invalid JSON: returns `None` and writes a
      warning to stderr mentioning the failure.
- [x] Cache file containing valid JSON but no `embeddings` key: returns
      `None` and writes a warning to stderr.
- [x] Cache file containing a valid payload: returns the `embeddings`
      dict (pre-existing behavior, must not regress).
- [x] Pre-existing tests in `tests/` continue to pass.

## Verification

- [x] `tests/test_corrupted_embeddings_cache.py::test_invalid_json_returns_none_with_warning`
      writes garbage bytes to the cache path, patches
      `DRIL_EMBEDDINGS_FILE`, and asserts `None` + stderr warning.
- [x] `test_missing_embeddings_key_returns_none_with_warning` writes a
      valid JSON object with no `embeddings` key and asserts the same.
- [x] `test_valid_cache_roundtrips` writes a valid payload and asserts
      the returned dict equals the embeddings dict (no regression).
- [x] `test_missing_cache_returns_none` (no file at path) returns `None`
      silently (no stderr noise).
- [x] All four new tests fail on unfixed code for the corrupt-cache
      paths and pass after the fix.
- [x] Full `pytest tests/` reports 12/12 passing (8 existing + 4 new).
