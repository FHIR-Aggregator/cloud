import os
from unittest.mock import patch

import pytest
import respx
from fastapi.testclient import TestClient
from fhir_proxy.proxy import adjust_urls
from httpx import Response


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
        return_value=Response(200, json={"resourceType": "Patient"})
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
    assert response.json() == {"resourceType": "Patient"}

    response = client.get(
        "/does-not-exist.txt",
        headers={
            "x-forwarded-host": "forwarded.example.com",
            "x-forwarded-proto": "https",
        },
    )

    assert response.status_code == 404
