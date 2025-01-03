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

assert DEFAULT_FHIR_SERVICE_URL, "DEFAULT_FHIR_SERVICE_URL not set?"

# Configure cache parameters
cache = TTLCache(maxsize=10, ttl=60)  # Cache up to 10 tokens, expire after 60 seconds

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
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=e.response.status_code, detail=e.response.reason
            )


def adjust_urls(content, forwarded_host, forwarded_proto) -> dict:
    """Rewrite the response to include the original request path."""
    # '.link[] | .url'
    # '.entry[] | .fullUrl'
    if forwarded_host:
        if "link" in content:
            for link in content["link"]:
                if "url" in link:
                    parsed_url = urlparse(link["url"])
                    resource = parsed_url.path
                    if resource.endswith("/"):
                        resource = resource[:-1]
                    resource = "/" + resource.split("/")[-1]
                    link["url"] = (
                        f"{forwarded_proto}://{forwarded_host}{resource}?{parsed_url.query}"
                    )
        if "entry" in content:
            for entry in content["entry"]:
                if "fullUrl" in entry:
                    parsed_url = urlparse(entry["fullUrl"])
                    resource = parsed_url.path
                    if resource.endswith("/"):
                        resource = resource[:-1]
                    resource = "/" + resource.split("/")[-1]
                    entry["fullUrl"] = (
                        f"{forwarded_proto}://{forwarded_host}{resource}?{parsed_url.query}"
                    )
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

    uvicorn.run(app, host="0.0.0.0", port=DEFAULT_PORT)
