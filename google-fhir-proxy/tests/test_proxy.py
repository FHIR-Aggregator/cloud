import json
import os
from unittest.mock import patch

import pytest
import respx
from fastapi.testclient import TestClient
from fhir_proxy.proxy import adjust_urls
from httpx import Response

# The backend FHIR store returns absolute `next`/`fullUrl` links pointing at
# itself. If the proxy doesn't rewrite them, clients follow them directly and
# get a 401 (the proxy holds the credentials). This is the literal URL shape
# from the reviewer's failing cholangiocarcinoma run.
BACKEND_NEXT_URL = (
    "https://healthcare.googleapis.com/v1beta1/projects/p/locations/us-west1/"
    "datasets/d/fhirStores/public/fhir/Condition/?code=70179006&_page_token=ABC123"
)


def test_adjust_urls():
    content = {
        "link": [
            {"url": "http://example.com/Patient?_id=123"},
            {"url": "http://example.com/Observation?_id=123"},
            {"url": "http://example.com/a/b/c/DocumentReference?_id=123"},
        ],
        "entry": [
            {"fullUrl": "http://example.com/Patient?_id=123"},
            {"fullUrl": "http://example.com/Observation?_id=123&foo=bar"},
            {"fullUrl": "http://example.com/a/b/c/DocumentReference?_id=123"},
            {"fullUrl": "http://example.com/a/b/c/DocumentReference/XXXXXXX"},
        ],
    }
    forwarded_host = "forwarded.example.com"
    forwarded_proto = "https"

    expected_content = {
        "link": [
            {"url": "https://forwarded.example.com/Patient?_id=123"},
            {"url": "https://forwarded.example.com/Observation?_id=123"},
            {"url": "https://forwarded.example.com/DocumentReference?_id=123"},
        ],
        "entry": [
            {"fullUrl": "https://forwarded.example.com/Patient?_id=123"},
            {"fullUrl": "https://forwarded.example.com/Observation?_id=123&foo=bar"},
            {"fullUrl": "https://forwarded.example.com/DocumentReference?_id=123"},
            {"fullUrl": "https://forwarded.example.com/DocumentReference/XXXXXXX"},
        ],
    }

    result = adjust_urls(content, forwarded_host, forwarded_proto)
    assert result == expected_content


@pytest.mark.asyncio
@respx.mock
@patch("fhir_proxy.proxy.fetch_token", return_value={"access_token": "mocked_token"})
async def test_fhir_proxy_get(mock_fetch_token):
    # Mock the target FHIR service URL
    from fhir_proxy.proxy import app

    assert os.getenv(
        "FHIR_SERVICE_URL"
    ), "FHIR_SERVICE_URL is not set. Please set env var to `http://example.com/fhir`"
    target_url = "http://example.com/fhir/Patient?_id=123"
    respx.get(target_url).mock(
        return_value=Response(200, json={"resourceType": "Bundle"})
    )

    target_url = "http://example.com/fhir/does-not-exist.txt"
    respx.get(target_url).mock(return_value=Response(404))

    # create a mock for the fetch_token function

    # Make a request to the proxy
    client = TestClient(app)
    response = client.get(
        "/Patient?_id=123",
        headers={
            "x-forwarded-host": "forwarded.example.com",
            "x-forwarded-proto": "https",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"resourceType": "Bundle"}

    response = client.get(
        "/does-not-exist.txt",
        headers={
            "x-forwarded-host": "forwarded.example.com",
            "x-forwarded-proto": "https",
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
@respx.mock
@patch.dict(os.environ, {"PUBLIC_BASE_URL": "https://proxy.example.org"})
@patch("fhir_proxy.proxy.fetch_token", return_value={"access_token": "mocked_token"})
async def test_next_link_rewritten_without_forwarded_headers(mock_fetch_token):
    """Regression: even when the front reverse proxy sends NO X-Forwarded-*
    headers, the backend pagination `next` link must be rewritten to the public
    host -- never leaked. A leaked backend URL is what caused the reviewer's run
    to 401 on page 2 and stop at 100/389 resources."""
    from fhir_proxy.proxy import app

    assert os.getenv("FHIR_SERVICE_URL"), "set FHIR_SERVICE_URL=http://example.com/fhir"

    respx.get("http://example.com/fhir/Condition").mock(
        return_value=Response(
            200,
            json={
                "resourceType": "Bundle",
                "link": [
                    {"relation": "self", "url": BACKEND_NEXT_URL},
                    {"relation": "next", "url": BACKEND_NEXT_URL},
                ],
            },
        )
    )

    client = TestClient(app)
    # NOTE: no x-forwarded-* headers on purpose -- this is the production case
    # the old code mishandled.
    response = client.get("/Condition", params={"code": "70179006"})

    assert response.status_code == 200
    next_link = next(l["url"] for l in response.json()["link"] if l["relation"] == "next")
    assert "healthcare.googleapis.com" not in next_link, f"backend URL leaked: {next_link}"
    assert next_link.startswith("https://proxy.example.org/Condition")
    assert "_page_token=ABC123" in next_link
