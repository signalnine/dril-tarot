"""
Regression test for dril-tarot-k2z.

screenshot_tweet previously called page.query_selector('.tweet-card') after
wait_for_selector and dereferenced the result without a None check, producing
a confusing AttributeError when the element disappeared between the two
calls. The fix uses the handle returned by wait_for_selector directly and
raises a descriptive RuntimeError if it's None.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import generate_dril_tarot_images as g


class _FakeHandle:
    def __init__(self, payload=b'PNG'):
        self._payload = payload
        self.calls = 0

    def screenshot(self, type='png'):
        self.calls += 1
        return self._payload


class _FakePage:
    """Configurable stand-in for a Playwright page.

    wait_handle: value returned from wait_for_selector
    query_handle: value returned from query_selector (fallback)
    """
    def __init__(self, wait_handle, query_handle=None):
        self._wait_handle = wait_handle
        self._query_handle = query_handle
        self.set_content_called = False
        self.query_calls = 0

    def set_content(self, html):
        self.set_content_called = True

    def wait_for_selector(self, selector):
        return self._wait_handle

    def query_selector(self, selector):
        self.query_calls += 1
        return self._query_handle


def _tweet():
    return {
        'tweet_id': '1',
        'tweet_content': 'hello',
        'tweet_url': 'http://x/1',
        'tweet_date': '2020-01-01',
        'retweets': 1,
        'favorites': 2,
    }


def test_uses_wait_for_selector_handle_directly():
    """The handle returned by wait_for_selector is enough; no second
    query_selector call should be needed on the happy path."""
    handle = _FakeHandle(payload=b'PNGDATA')
    page = _FakePage(wait_handle=handle)

    result = g.screenshot_tweet(page, _tweet())

    assert result == b'PNGDATA'
    assert handle.calls == 1
    assert page.query_calls == 0, (
        "happy path must not race a second query_selector against the page"
    )


def test_missing_element_raises_descriptive_error():
    """Both wait_for_selector and query_selector returning None must produce
    a clear RuntimeError, not AttributeError: 'NoneType' has no attribute
    'screenshot'."""
    page = _FakePage(wait_handle=None, query_handle=None)

    with pytest.raises(RuntimeError, match=r"\.tweet-card"):
        g.screenshot_tweet(page, _tweet())


def test_falls_back_to_query_selector_when_wait_returns_none():
    """If wait_for_selector returns None but query_selector finds the
    element, we still succeed -- treat this as a benign race recovery."""
    handle = _FakeHandle(payload=b'RECOVERED')
    page = _FakePage(wait_handle=None, query_handle=handle)

    result = g.screenshot_tweet(page, _tweet())

    assert result == b'RECOVERED'
    assert page.query_calls == 1
