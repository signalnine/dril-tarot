# CONTRACT: Replace deprecated datetime.utcnow() in match_dril_tweets

Tracks bd issue `dril-tarot-dyd`.

## Problem

`match_dril_tweets.py` stamps `generated_at` in two places
(`save_tweet_embeddings` and `save_results`) via
`datetime.utcnow().isoformat() + 'Z'`. Python 3.12 deprecated
`datetime.utcnow()` and it is scheduled for removal; running the script on
3.12+ already prints a `DeprecationWarning`, and a future Python will break
the script outright. The naive datetime it produces is also a subtle
correctness trap -- the value is UTC only by convention, not by type.

## Behaviors required

- [x] Calling `save_tweet_embeddings` does not emit `DeprecationWarning`.
- [x] Calling `save_results` does not emit `DeprecationWarning`.
- [x] The serialized `generated_at` field keeps its existing
      `...microsecondsZ` shape so previously-written JSON consumers still
      match (Z suffix, no raw `+00:00` offset).
- [x] Pre-existing tests (`tests/test_avatar_base64.py`,
      `tests/test_missing_screenshot.py`,
      `tests/test_transparent_composite.py`) continue to pass.

## Verification

- [x] `tests/test_timestamp_format.py::test_save_tweet_embeddings_is_deprecation_free_and_keeps_z_suffix`
      promotes `DeprecationWarning` to error, calls `save_tweet_embeddings`,
      and asserts the written timestamp ends with `'Z'` and contains no
      `'+00:00'`.
- [x] `test_save_results_is_deprecation_free_and_keeps_z_suffix` does the
      same for `save_results`.
- [x] Both tests fail on unfixed code with
      `DeprecationWarning: datetime.datetime.utcnow() is deprecated`.
- [x] Full `pytest tests/` reports 8/8 passing after the fix.
