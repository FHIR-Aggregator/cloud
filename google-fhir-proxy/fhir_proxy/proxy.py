import logging
import os
from urllib.parse import urlparse

import httpx
import requests
from cachetools import TTLCache
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_FHIR_SERVICE_URL = os.environ.get("FHIR_SERVICE_URL", None)
DEFAULT_PORT = int(os.environ.get("PORT", 8080))

# Configure cache parameters
# The default expiration time for a Google access token is one hour (3,600 seconds).
# We will cache the token for 1800 seconds to avoid unnecessary requests.
cache = TTLCache(
    maxsize=10, ttl=1800
)  # Cache up to 10 tokens, expire after 1800 seconds

if not DEFAULT_FHIR_SERVICE_URL:
    logger.warning(
        "FHIR_SERVICE_URL not set, please set the environment variable or specify on command line."
    )
else:
    logger.info(f"DEFAULT_FHIR_SERVICE_URL: {DEFAULT_FHIR_SERVICE_URL}")

app = FastAPI()


def fetch_token():
    """Fetches an access token from the metadata server, FOR GCP environments only."""
    try:
        response = requests.get(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        logger.error(f"Error fetching token: {e}")
        return None


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    token = cache.get("access_token")
    if not token:
        token = fetch_token()
        if token:
            cache["access_token"] = token

    if not token:
        raise HTTPException(status_code=500, detail="Failed to obtain access token")

    request.state.token = token
    response = await call_next(request)
    return response


@app.get("/{path:path}")
async def proxy_get(request: Request, path: str):
    parsed_url = urlparse(request.url._url)  # noqa: disable=protected-access
    request_path = parsed_url.path
    request_query = parsed_url.query

    target_url = f"{DEFAULT_FHIR_SERVICE_URL}{request_path}?{request_query}"
    headers = {"Authorization": f"Bearer {request.state.token}"}
    logger.debug(f"target_url: >{target_url}< {headers}")
    logger.debug(f"request.headers: {request.headers}")
    forwarded_host = request.headers.get("x-forwarded-host", None)
    forwarded_proto = request.headers.get("x-forwarded-proto", None)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(target_url, headers=headers)
            response.raise_for_status()
            content = response.json()
            content = adjust_urls(content, forwarded_host, forwarded_proto)

            return JSONResponse(content=content, status_code=response.status_code)
        except httpx.HTTPStatusError as e:

            raise HTTPException(
                status_code=e.response.status_code, detail=e.response.reason_phrase
            )


def adjust_urls(content, forwarded_host, forwarded_proto) -> dict:
    """Rewrite the response to include the original request path."""
    # '.link[] | .url'
    # '.entry[] | .fullUrl'

    def _adjust_url(url):
        """Adjust the URL to include the original request path."""
        parsed_url = urlparse(url)
        if "?" in url:
            # this is a query
            resource = parsed_url.path
            if resource.endswith("/"):
                resource = resource[:-1]
            resource = "/" + resource.split("/")[-1]
            adjusted_url = (
                f"{forwarded_proto}://{forwarded_host}{resource}?{parsed_url.query}"
            )
            if adjusted_url.endswith("?"):
                adjusted_url = adjusted_url[:-1]
            return adjusted_url
        else:
            # this is a resource, get last two elements of path
            resource_with_id = "/" + "/".join(parsed_url.path.split("/")[-2:])
            return f"{forwarded_proto}://{forwarded_host}{resource_with_id}"

    if forwarded_host:
        if "link" in content:
            for link in content["link"]:
                if "url" in link:
                    link["url"] = _adjust_url(link["url"])
        if "entry" in content:
            for entry in content["entry"]:
                if "fullUrl" in entry:
                    entry["fullUrl"] = _adjust_url(entry["fullUrl"])
    return content


@app.post("/{path:path}")
async def proxy_post(path: str):
    raise HTTPException(status_code=403, detail="Forbidden")


@app.put("/{path:path}")
async def proxy_put(path: str):
    raise HTTPException(status_code=403, detail="Forbidden")


@app.delete("/{path:path}")
async def proxy_delete(path: str):
    raise HTTPException(status_code=403, detail="Forbidden")


if __name__ == "__main__":
    import uvicorn

    DEFAULT_FHIR_SERVICE_URL = os.environ.get("FHIR_SERVICE_URL", None)
    assert (
        DEFAULT_FHIR_SERVICE_URL
    ), "FHIR_SERVICE_URL not set, please set the environment variable or specify on command line."

    uvicorn.run(app, host="0.0.0.0", port=DEFAULT_PORT)
