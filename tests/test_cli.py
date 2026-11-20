import importlib.util
import os
import subprocess
import sys

import pytest

from conftest import ROOT

has_scrapling = importlib.util.find_spec("scrapling") is not None
has_cloak = importlib.util.find_spec("cloakbrowser") is not None
browser_tests = os.environ.get("RUN_BROWSER_TESTS") == "1"

needs_scrapling = pytest.mark.skipif(not has_scrapling, reason="scrapling not installed")
needs_cloak = pytest.mark.skipif(not (has_cloak and browser_tests),
                                 reason="set RUN_BROWSER_TESTS=1 with cloakbrowser installed")


@needs_scrapling
def test_scrapling_full_text(server, run_script):
    code, env = run_script("scrapling-extract.py", f"{server}/quotes.html")
    assert code == 0 and env["ok"]
    assert "שלום עולם" in env["data"]["text"] and "Author Two" in env["data"]["text"]


@needs_scrapling
def test_scrapling_css_nested_text(server, run_script):
    code, env = run_script("scrapling-extract.py", f"{server}/quotes.html", "--css", ".quote")
    assert code == 0 and env["data"]["count"] == 2
    assert env["data"]["items"][1] == "Second quote Author Two"


@needs_scrapling
@pytest.mark.parametrize("path,error_type,code", [
    ("/status/404", "NOT_FOUND", 4),
    ("/status/429", "RATE_LIMITED", 6),
    ("/status/500", "HTTP_ERROR", 5),
    ("/challenge", "BLOCKED", 7),
    ("/empty.html", "EMPTY_RESULT", 3),
])
def test_scrapling_errors(server, run_script, path, error_type, code):
    rc, env = run_script("scrapling-extract.py", f"{server}{path}", "--retries", "0")
    assert (rc, env["error_type"], env["ok"]) == (code, error_type, False)
    assert env["hint"]


@needs_scrapling
def test_scrapling_429_reports_retry_after(server, run_script):
    _, env = run_script("scrapling-extract.py", f"{server}/status/429", "--retries", "0")
    assert env["retry_after"] == 1.0 and env["retryable"] is True


@needs_scrapling
def test_scrapling_retries_5xx(server, run_script):
    code, env = run_script("scrapling-extract.py", f"{server}/flaky", "--css", ".quote")
    assert code == 0 and env["status"] == 200 and env["data"]["count"] == 2


@needs_scrapling
def test_scrapling_cf_footer_is_not_blocked(server, run_script):
    code, env = run_script("scrapling-extract.py", f"{server}/cf-footer.html")
    assert code == 0 and env["ok"]


@needs_scrapling
def test_scrapling_empty_selector(server, run_script):
    code, env = run_script("scrapling-extract.py", f"{server}/delayed.html", "--css", ".item")
    assert (code, env["error_type"]) == (3, "EMPTY_RESULT")


def test_scrapling_wait_for_requires_stealth():
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "scrapling-extract.py"), "http://x", "--wait-for", ".a"],
                          capture_output=True, text=True)
    assert proc.returncode == 2 and "--stealth" in proc.stderr


def test_login_flow_importable():
    sys.path.insert(0, str(ROOT))
    from scripts.login_flow import LoginResult, classify_result, harvest_api, login  # noqa: F401
    assert LoginResult.SUCCESS.value == "SUCCESS"


@needs_cloak
def test_cloak_wait_for_selector(server, run_script):
    code, env = run_script("cloak-scrape.py", f"{server}/delayed.html", "--css", ".item", "--wait-for", ".item")
    assert code == 0 and env["data"]["count"] == 3


@needs_cloak
def test_cloak_without_wait_for_misses_late_content(server, run_script):
    code, env = run_script("cloak-scrape.py", f"{server}/delayed.html", "--css", ".item", "--wait", "0")
    assert (code, env["error_type"]) == (3, "EMPTY_RESULT")


@needs_cloak
def test_cloak_wait_for_timeout(server, run_script):
    code, env = run_script("cloak-scrape.py", f"{server}/quotes.html", "--wait-for", ".never", "--timeout", "3000")
    assert (code, env["error_type"]) == (8, "TIMEOUT")


@needs_cloak
@pytest.mark.parametrize("path,error_type", [
    ("/status/404", "NOT_FOUND"),
    ("/status/429", "RATE_LIMITED"),
])
def test_cloak_status_errors(server, run_script, path, error_type):
    _, env = run_script("cloak-scrape.py", f"{server}{path}", "--retries", "0", "--wait", "0")
    assert env["error_type"] == error_type


@needs_cloak
def test_cloak_empty_body_404_is_not_found(server, run_script):
    code, env = run_script("cloak-scrape.py", f"{server}/empty-status/404", "--wait-for", ".x")
    assert (code, env["error_type"], env["status"]) == (4, "NOT_FOUND", 404)
    assert env["final_url"].endswith("/empty-status/404")


@needs_cloak
def test_cloak_wait_for_response(server, run_script):
    code, env = run_script("cloak-scrape.py", f"{server}/xhr.html", "--css", ".row",
                           "--wait-for-response", r"data\.json", "--wait-for", ".row")
    assert code == 0 and env["data"]["items"] == ["Row one", "Row two"]


@needs_cloak
def test_cloak_wait_for_response_skipped_on_error_page(server, run_script):
    code, env = run_script("cloak-scrape.py", f"{server}/status/404", "--wait-for-response", "never-sent",
                           "--timeout", "20000", "--retries", "0")
    assert (code, env["error_type"]) == (4, "NOT_FOUND") and env["elapsed_ms"] < 15000


@needs_cloak
def test_cloak_wait_for_response_timeout(server, run_script):
    code, env = run_script("cloak-scrape.py", f"{server}/quotes.html", "--wait-for-response", "never-sent",
                           "--timeout", "2000")
    assert (code, env["error_type"]) == (8, "TIMEOUT")


@needs_cloak
def test_cloak_challenge_is_blocked(server, run_script):
    code, env = run_script("cloak-scrape.py", f"{server}/challenge", "--retries", "0", "--wait", "0", "--timeout", "3000")
    assert (code, env["error_type"]) == (7, "BLOCKED")


@needs_cloak
def test_cloak_retries_5xx(server, run_script):
    code, env = run_script("cloak-scrape.py", f"{server}/flaky", "--css", ".quote", "--wait-for", ".quote")
    assert code == 0 and env["status"] == 200


@needs_cloak
def test_cloak_output_file_utf8(server, run_script, tmp_path):
    target = tmp_path / "out.txt"
    code, _ = run_script("cloak-scrape.py", f"{server}/quotes.html", "--text", "--wait", "0", "-o", str(target))
    assert code == 0 and "שלום עולם" in target.read_text(encoding="utf-8")
