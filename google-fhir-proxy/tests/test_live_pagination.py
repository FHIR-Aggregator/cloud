"""Live acceptance test for the pagination-401 fix (cloud PR #13).

Unlike test_proxy.py (which unit-tests adjust_urls against a mock), this hits the
*deployed* proxy over the network and asserts the end-to-end behavior an
anonymous user sees. It encodes the reviewer's reproduction as a pass/fail gate:

  - FAILS while the bug is live: the proxy leaks the Google Healthcare backend
    URL in the `next` link, so an unauthenticated client 401s on page 2 and
    `fq run` stops at 100/389 resources.
  - PASSES once PR #13 is deployed: links are rewritten to the proxy host and
    page 2 is fetchable with no credentials.

It is OPT-IN (network + prod) and skipped by default. Run with:

    RUN_LIVE_TESTS=1 pytest google-fhir-proxy/tests/test_live_pagination.py -v

No FHIR_SERVICE_URL or proxy dependencies are needed -- this test is stdlib-only
and does not import the proxy app.
"""
import json
import os
import urllib.error
import urllib.request

import pytest

PROXY_URL = "https://google-fhir.fhir-aggregator.org/Condition?code:code=70179006"
BACKEND_HOST = "healthcare.googleapis.com"

live = pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_TESTS"),
    reason="live test against the deployed proxy; set RUN_LIVE_TESTS=1 to run",
)


def _get(url):
    """GET a URL -> (status, parsed_json). Skips the test if the network is down."""
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except urllib.error.URLError as e:
        pytest.skip(f"network unavailable: {e}")


@live
def test_proxy_does_not_leak_backend_pagination_url():
    """The proxy must rewrite pagination links to its own host, never leak the backend."""
    status, page1 = _get(PROXY_URL)
    assert status == 200, f"page 1 returned {status}"

    next_links = [l["url"] for l in page1.get("link", []) if l.get("relation") == "next"]
    assert next_links, "no `next` link on page 1 (cannot evaluate pagination)"
    next_url = next_links[0]

    assert BACKEND_HOST not in next_url, (
        f"proxy leaked the backend URL in the `next` link -> anonymous clients 401 on "
        f"page 2 (the reviewer's 100/389 failure). PR #13 not deployed.\n  next = {next_url}"
    )


@live
def test_anonymous_user_can_paginate_past_page_one():
    """An unauthenticated client must be able to fetch page 2 (no Google creds)."""
    status, page1 = _get(PROXY_URL)
    assert status == 200, f"page 1 returned {status}"

    next_links = [l["url"] for l in page1.get("link", []) if l.get("relation") == "next"]
    assert next_links, "no `next` link on page 1"

    status2, _ = _get(next_links[0])
    assert status2 == 200, (
        f"page 2 returned {status2}; pagination still broken for anonymous users "
        f"(backend URL leaked and rejected the credential-less request)."
    )