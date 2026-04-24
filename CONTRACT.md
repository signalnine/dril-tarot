# CONTRACT: main() must regenerate embeddings when cache load returns None

Tracks bd issue `dril-tarot-dnj`.

## Problem

The earlier fix (commit 270ef6f) made `load_tweet_embeddings()` return
`None` on a missing or corrupt cache, with the intent that the caller
would fall through to regeneration. But the caller in `main()` does not
handle `None`:

```python
else:
    print("\nLoading cached tweet embeddings...")
    tweet_embeddings = load_tweet_embeddings()
    print(f"✓ Loaded {len(tweet_embeddings)} cached embeddings")
```

When the cache is corrupt, `load_tweet_embeddings()` returns `None`
(with a stderr warning), then `len(None)` raises `TypeError` and the
script aborts. Same outcome as before the fix, just one frame deeper.
The "degrades to regenerate from scratch" promise in the helper's
docstring is not actually delivered end-to-end.

## Behaviors required

- [x] When `load_tweet_embeddings()` returns `None` in `main()` (cache
      file present but corrupt), `main()` must regenerate embeddings via
      `generate_tweet_embeddings()` and persist them via
      `save_tweet_embeddings()`, just like the `--regenerate-embeddings`
      / missing-file branch.
- [x] When the cache loads successfully, behavior is unchanged: log the
      count of loaded embeddings and proceed.
- [x] Pre-existing tests in `tests/` continue to pass.

## Verification

- [x] New test `tests/test_main_corrupt_cache_regenerates.py` patches
      `DRIL_EMBEDDINGS_FILE` to a corrupt file, stubs the OpenAI client
      and `generate_tweet_embeddings` / `save_tweet_embeddings`, runs
      `main()`, and asserts:
      - `main()` returns normally (no `TypeError`, no `SystemExit` from
        the catch-all).
      - `generate_tweet_embeddings` was called.
      - `save_tweet_embeddings` was called.
- [x] Test fails on unfixed code with a `TypeError: object of type
      'NoneType' has no len()`.
- [x] Test passes after the fix.
- [x] `pytest tests/` reports all tests passing (13/13: 12 existing + 1 new).
