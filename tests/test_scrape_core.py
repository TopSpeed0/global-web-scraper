import time
from email.utils import formatdate

import pytest

import scrape_core as core


@pytest.mark.parametrize("status,title,html,expected", [
    (200, "Quotes", "<p>ok</p>", None),
    (200, "Normal page", '<script src="/cdn-cgi/challenge-platform/scripts/jsd/main.js"></script>'
                         "<footer>Performance &amp; security by Cloudflare</footer>", None),
    (403, "Just a moment...", "", core.BLOCKED),
    (200, "Sign in", '<div id="cf-browser-verification"></div>', core.BLOCKED),
    (404, "Not found", "", core.NOT_FOUND),
    (410, "Gone", "", core.NOT_FOUND),
    (429, "Too many", "", core.RATE_LIMITED),
    (403, "Forbidden", "", core.HTTP_ERROR),
    (503, "Busy", "", core.HTTP_ERROR),
    (None, None, None, None),
])
def test_classify_page(status, title, html, expected):
    assert core.classify_page(status, title, html) == expected


def test_parse_retry_after():
    assert core.parse_retry_after("7") == 7.0
    assert core.parse_retry_after(None) is None
    assert core.parse_retry_after("soon") is None
    future = core.parse_retry_after(formatdate(time.time() + 60, usegmt=True))
    assert 50 <= future <= 61


def test_backoff_is_capped():
    assert core.backoff_seconds(0, retry_after=999) == core.MAX_RETRY_WAIT_S
    assert 1.5 <= core.backoff_seconds(0) <= 2.0


class TimeoutError(Exception):
    pass


@pytest.mark.parametrize("exc,expected", [
    (TimeoutError("Timeout 30000ms exceeded."), core.TIMEOUT),
    (core.WaitTimeoutError("no response matching 'x'"), core.TIMEOUT),
    (RuntimeError("Failed to perform, curl: (28) Operation timed out"), core.TIMEOUT),
    (RuntimeError("Page.goto: net::ERR_NAME_NOT_RESOLVED at https://x.invalid/"), core.NAVIGATION_ERROR),
    (RuntimeError("curl: (7) Failed to connect to 127.0.0.1 port 9"), core.NAVIGATION_ERROR),
    (RuntimeError("something odd"), core.UNKNOWN_ERROR),
])
def test_classify_exception(exc, expected):
    assert core.classify_exception(exc) == expected


def test_envelope_success():
    result = core.Result(tool="t", url="u", status=200, data={"text": "x"})
    envelope = result.to_dict()
    assert envelope["ok"] is True and envelope["error_type"] is None and envelope["hint"] is None
    assert result.exit_code == 0 and envelope["retryable"] is False


@pytest.mark.parametrize("error_type,status,code,retryable", [
    (core.EMPTY_RESULT, 200, 3, False),
    (core.NOT_FOUND, 404, 4, False),
    (core.HTTP_ERROR, 403, 5, False),
    (core.HTTP_ERROR, 502, 5, True),
    (core.RATE_LIMITED, 429, 6, True),
    (core.BLOCKED, 403, 7, False),
    (core.TIMEOUT, None, 8, True),
    (core.NAVIGATION_ERROR, None, 9, True),
    ("TWO_FACTOR", None, 11, False),
    ("SOMETHING_NEW", None, 1, False),
])
def test_envelope_failure(error_type, status, code, retryable):
    result = core.Result(tool="t", url="u", status=status).fail(error_type, "m")
    envelope = result.to_dict()
    assert envelope["ok"] is False and envelope["error_type"] == error_type
    assert envelope["hint"]
    assert result.exit_code == code
    assert envelope["retryable"] is retryable


def test_retryable_override():
    result = core.Result(tool="login-flow", url="u", retryable_override=False).fail(core.TIMEOUT)
    assert result.retryable is False
