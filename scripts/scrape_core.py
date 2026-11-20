"""Shared helpers for the scraper scripts.

- checked navigation with status-aware retries (``goto_checked``)
- readiness waits instead of fixed sleeps (``wait_ready``)
- one result envelope, error taxonomy and exit codes (``Result``)

Patterns adapted from eshaham/israeli-bank-scrapers (MIT): ``navigateTo`` retry on
non-OK status, ``waitUntil``/``waitForUrl`` readiness helpers, and the
``{success, errorType, errorMessage}`` result object that is returned, never thrown.
"""
import json
import random
import re
import sys
import time
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from typing import Any, Optional

NOT_FOUND = "NOT_FOUND"
HTTP_ERROR = "HTTP_ERROR"
RATE_LIMITED = "RATE_LIMITED"
BLOCKED = "BLOCKED"
TIMEOUT = "TIMEOUT"
NAVIGATION_ERROR = "NAVIGATION_ERROR"
EMPTY_RESULT = "EMPTY_RESULT"
INVALID_ARGUMENT = "INVALID_ARGUMENT"
UNKNOWN_ERROR = "UNKNOWN_ERROR"

LOGIN_NEEDS_USER = ("INVALID_PASSWORD", "ACCOUNT_BLOCKED", "CHANGE_PASSWORD", "CAPTCHA_REQUIRED", "TWO_FACTOR")

EXIT_CODES = {
    None: 0,
    UNKNOWN_ERROR: 1,
    INVALID_ARGUMENT: 2,
    EMPTY_RESULT: 3,
    NOT_FOUND: 4,
    HTTP_ERROR: 5,
    RATE_LIMITED: 6,
    BLOCKED: 7,
    "CLOUDFLARE_BLOCKED": 7,
    "AUTOMATION_BLOCKED": 7,
    TIMEOUT: 8,
    NAVIGATION_ERROR: 9,
    **{name: 11 for name in LOGIN_NEEDS_USER},
}

HINTS = {
    NOT_FOUND: "The URL does not exist. Check it or search for the current one.",
    HTTP_ERROR: "The server returned an error status. 5xx may clear on retry; 401/403 may mean bot blocking, so escalate to CloakBrowser.",
    RATE_LIMITED: "Wait for retry_after seconds (or a few minutes) before retrying. Slow down.",
    BLOCKED: "Anti-bot challenge page. Escalate to cloak-scrape.py; if it is already CloakBrowser, try --humanize or ask the user.",
    "CLOUDFLARE_BLOCKED": "Anti-bot challenge page. Try --humanize or ask the user.",
    "AUTOMATION_BLOCKED": "The site detected automation. Stop and ask the user.",
    TIMEOUT: "The page or the awaited element did not arrive in time. Retry once, raise --timeout, or check the --wait-for selector.",
    NAVIGATION_ERROR: "Network or DNS failure reaching the site. Check the URL and connectivity, then retry.",
    EMPTY_RESULT: "Nothing matched. The page may need JavaScript (use --stealth or cloak-scrape.py with --wait-for) or the selector is wrong.",
    INVALID_ARGUMENT: "Fix the command arguments.",
    "CAPTCHA_REQUIRED": "A CAPTCHA is shown. Ask the user to complete it; do not retry automatically.",
    "TWO_FACTOR": "The site asks for a one-time code. Ask the user; do not retry automatically.",
    "INVALID_PASSWORD": "The site rejected the credentials. Ask the user; do not retry (lockout risk).",
    "ACCOUNT_BLOCKED": "The account is locked. The user must resolve it on the site.",
    "CHANGE_PASSWORD": "The site requires a password change. The user must do it on the site.",
    UNKNOWN_ERROR: "Unclassified failure. Run again with a visible browser or check the page manually.",
}

RETRYABLE = {RATE_LIMITED, TIMEOUT, NAVIGATION_ERROR}

CHALLENGE_TITLES = (
    "just a moment",
    "attention required! | cloudflare",
    "verifying you are human",
    "pardon our interruption",
    "ddos-guard",
)
CHALLENGE_MARKERS = (
    "_cf_chl_opt",
    "cf-browser-verification",
    'id="challenge-form"',
    "captcha-delivery.com",
    'id="px-captcha"',
)

MAX_RETRY_WAIT_S = 30.0


@dataclass
class Result:
    tool: str
    url: str
    ok: bool = True
    error_type: Optional[str] = None
    message: str = ""
    final_url: Optional[str] = None
    status: Optional[int] = None
    title: Optional[str] = None
    retry_after: Optional[float] = None
    data: Any = None
    retryable_override: Optional[bool] = None
    started: float = field(default_factory=time.monotonic, repr=False)

    def fail(self, error_type, message="", retry_after=None):
        self.ok = False
        self.error_type = error_type
        self.message = message
        if retry_after is not None:
            self.retry_after = retry_after
        return self

    @property
    def retryable(self):
        if self.ok:
            return False
        if self.retryable_override is not None:
            return self.retryable_override
        if self.error_type == HTTP_ERROR:
            return bool(self.status and self.status >= 500)
        return self.error_type in RETRYABLE

    @property
    def exit_code(self):
        if self.ok:
            return 0
        return EXIT_CODES.get(self.error_type, 1)

    def to_dict(self):
        return {
            "ok": self.ok,
            "error_type": self.error_type,
            "retryable": self.retryable,
            "message": self.message,
            "hint": None if self.ok else HINTS.get(self.error_type, HINTS[UNKNOWN_ERROR]),
            "url": self.url,
            "final_url": self.final_url,
            "status": self.status,
            "title": self.title,
            "retry_after": self.retry_after,
            "elapsed_ms": int((time.monotonic() - self.started) * 1000),
            "tool": self.tool,
            "data": self.data,
        }

    def emit(self, as_json, print_human):
        """Print the result and return the process exit code."""
        if as_json:
            print(json.dumps(self.to_dict(), ensure_ascii=False, indent=2))
        else:
            if self.ok or self.data is not None:
                print_human(self)
            if not self.ok:
                hint = HINTS.get(self.error_type, HINTS[UNKNOWN_ERROR])
                status = f" (HTTP {self.status})" if self.status else ""
                print(f"ERROR {self.error_type}{status}: {self.message}\nHint: {hint}", file=sys.stderr)
        return self.exit_code


def configure_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def parse_retry_after(value):
    """Seconds from a Retry-After header (delta-seconds or HTTP date), or None."""
    if not value:
        return None
    value = str(value).strip()
    if value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    return max(0.0, when.timestamp() - time.time())


def header(headers, name):
    if not headers:
        return None
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return value
    return None


def is_challenge(title, html):
    lowered_title = (title or "").strip().lower()
    if any(lowered_title.startswith(t) for t in CHALLENGE_TITLES):
        return True
    snippet = (html or "")[:200_000]
    return any(marker in snippet for marker in CHALLENGE_MARKERS)


def classify_page(status, title=None, html=None):
    """Error type for a fetched page, or None when it looks usable.

    Challenge detection uses the page title and structural markers only, never
    prose in the body, so a footer that says "Cloudflare" is not a block.
    """
    if is_challenge(title, html):
        return BLOCKED
    if status is None:
        return None
    if status in (404, 410):
        return NOT_FOUND
    if status == 429:
        return RATE_LIMITED
    if status >= 400:
        return HTTP_ERROR
    return None


def classify_exception(exc):
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    if "timeout" in name or "timed out" in text or "timeout" in text:
        return TIMEOUT
    if any(token in text for token in ("net::err_", "ns_error", "could not resolve", "failed to connect",
                                       "connection refused", "connection reset", "name or service not known")):
        return NAVIGATION_ERROR
    return UNKNOWN_ERROR


def first_line(exc, limit=300):
    text = str(exc).strip().splitlines()
    return (text[0] if text else type(exc).__name__)[:limit]


def should_retry_status(status):
    return status is not None and (status == 429 or status >= 500)


def backoff_seconds(attempt, retry_after=None):
    if retry_after is not None:
        return min(retry_after, MAX_RETRY_WAIT_S)
    return min(1.5 * (attempt + 1) + random.uniform(0, 0.5), MAX_RETRY_WAIT_S)


class WaitTimeoutError(Exception):
    pass


def goto_checked(page, url, timeout_ms=30_000, retries=1, wait_until="load", wait_for_response=None):
    """Navigate, retrying on 429/5xx. Returns the main-frame response (may be None).

    Chromium aborts error responses with an empty body (ERR_HTTP_RESPONSE_CODE_FAILURE);
    the response is still captured here so the caller sees the real status.

    With ``wait_for_response`` (a regex), also waits until a response whose URL
    matches arrives, so content loaded by XHR is ready before extraction. The wait
    is skipped when the page itself failed.
    """
    pattern = re.compile(wait_for_response) if wait_for_response else None
    state = {"nav": None, "matched": False}

    def on_response(r):
        if r.request.is_navigation_request() and r.frame == page.main_frame:
            state["nav"] = r
        if pattern and pattern.search(r.url):
            state["matched"] = True

    page.on("response", on_response)
    try:
        response = None
        for attempt in range(retries + 1):
            state.update(nav=None, matched=False)
            try:
                response = page.goto(url, timeout=timeout_ms, wait_until=wait_until)
            except Exception as exc:
                if "ERR_HTTP_RESPONSE_CODE_FAILURE" not in str(exc) or state["nav"] is None:
                    raise
                response = state["nav"]
            status = response.status if response else None
            if attempt < retries and should_retry_status(status) and not page_is_challenge(page):
                delay = backoff_seconds(attempt, parse_retry_after(header(response.headers, "retry-after")))
                page.wait_for_timeout(int(delay * 1000))
                continue
            break
        if pattern and classify_page(status) is None and not page_is_challenge(page):
            deadline = time.monotonic() + timeout_ms / 1000
            while not state["matched"]:
                if time.monotonic() >= deadline:
                    raise WaitTimeoutError(f"Timeout {timeout_ms}ms: no response matching {wait_for_response!r}")
                page.wait_for_timeout(100)
        return response
    finally:
        page.remove_listener("response", on_response)


def page_is_challenge(page):
    try:
        return is_challenge(page.title(), page.content())
    except Exception:
        return False


def wait_challenge_clear(page, timeout_ms=20_000, interval_ms=500):
    """Give an interstitial challenge time to resolve itself. True once it is gone."""
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if not page_is_challenge(page):
            return True
        page.wait_for_timeout(interval_ms)
    return not page_is_challenge(page)


def wait_ready(page, selector=None, url_regex=None, timeout_ms=30_000, fixed_ms=0):
    """Wait for the page to be ready: URL pattern, then selector, then an optional fixed pause."""
    if url_regex:
        page.wait_for_url(re.compile(url_regex), timeout=timeout_ms)
    if selector:
        page.wait_for_selector(selector, state="attached", timeout=timeout_ms)
    if fixed_ms:
        page.wait_for_timeout(fixed_ms)
