import logging
import os
from collections import defaultdict
from typing import Any
from urllib.parse import urlparse

import httpx
import requests
from cachetools import TTLCache, Cache
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, ORJSONResponse
import orjson

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_FHIR_SERVICE_URL = os.environ.get("FHIR_SERVICE_URL", None)
DEFAULT_PORT = int(os.environ.get("PORT", 8080))

# Configure cache parameters

# The default expiration time for a Google access token is one hour (3,600 seconds).
# We will cache the token for 1800 seconds to avoid unnecessary requests.
token_cache = TTLCache(
    maxsize=10, ttl=1800
)  # Cache up to 10 tokens, expire after 1800 seconds

# We will cache the vocabularies for infinite time, as they are not expected to change frequently.
vocabulary_cache = Cache(
    maxsize=100
)  # Cache up to 100 tokens, dont expire


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
async def add_service_account_header(request: Request, call_next):
    token = token_cache.get("access_token")
    if not token:
        token = fetch_token()
        if token:
            token_cache["access_token"] = token

    if not token:
        raise HTTPException(status_code=500, detail="Failed to obtain access token")

    request.state.token = token
    response = await call_next(request)
    return response


def extract_display_values(resource: dict[str, Any], code_dict: dict[str, int] = defaultdict(int), category_dict: dict[str, int] = defaultdict(int)) -> (dict[str, int], dict[str, int]):
    """
    Extracts display values from `code.coding` and `category.coding`
    and maintains a count dictionary.

    Args:
        resource (dict): A FHIR resource dictionary.
        code_dict (Dict[str, int], optional): A dictionary to store code display values and their counts. Defaults to defaultdict(int).
        category_dict (Dict[str, int], optional): A dictionary to store category display values and their counts. Defaults to defaultdict(int).

    Returns:
        Tuple[Dict[str, int], Dict[str, int]]: A tuple containing the code and category dictionaries.
    """

    # Extract from code.coding.display
    if "code" in resource and "coding" in resource["code"]:
        for coding in resource["code"]["coding"]:
            if "display" in coding:
                code_dict[coding["display"]] += 1

    # Extract from category.coding.display
    if "category" in resource:
        if isinstance(resource["category"], list):  # Handle list of categories
            for category in resource["category"]:
                if "coding" in category:
                    for coding in category["coding"]:
                        if "display" in coding:
                            category_dict[coding["display"]] += 1

    return code_dict, category_dict


def extract_extension_values(resource: dict[str, Any], extension_dict: dict[str, int] = defaultdict(int)) -> dict[str, int]:
    """
    Extracts values from `extension.value[x]` fields and maintains a count dictionary.

    Args:
        resource (dict): A FHIR resource dictionary.
        extension_dict (Dict[str, int], optional): A dictionary to store extension values and their counts. Defaults to defaultdict(int).

    Returns:
        Dict[str, int]: A dictionary with extension values as keys and their counts as values.
    """

    for ext in resource.get("extension", []):
        v = next(iter([ext[k] for k in ext.keys() if k.startswith("value")]), None)
        if isinstance(v, dict):
            v = '|'.join([str(_) for _ in v.values()])
        extension_dict[str(v)] += 1

    return extension_dict


def render_as_fhir_parameters(count_dict: dict[str, int]) -> dict[str, Any]:
    """
    Converts the count dictionary into a FHIR `Parameters` resource.

    Args:
        count_dict (Dict[str, int]): Dictionary with display values and their counts.

    Returns:
        Dict[str, Any]: A FHIR Parameters resource.
    """
    return {
        "resourceType": "Parameters",
        "parameter": [
            {"name": key, "valueInteger": value}
            for key, value in count_dict.items()
        ]
    }


@app.get("/{resource_type}/$vocabulary")
async def get_vocabulary(request: Request, resource_type: str):
    """Return a vocabulary for the specified resource type.

    Extracts display values from code.coding.display and category.coding.display.
    Counts occurrences of each display value.
    Formats output as a FHIR Parameters resource, nesting the counts inside a "parameter" list.

    """

    parsed_url = urlparse(request.url._url)  # noqa: disable=protected-access
    request_query = parsed_url.query
    request_query = request_query + f"{'&' if request_query else '?'}_elements=extension,category,code,type"
    target_url = f"{DEFAULT_FHIR_SERVICE_URL}/{resource_type}{request_query}"

    if vocabulary_cache.get(target_url):
        return ORJSONResponse(content=vocabulary_cache.get(target_url))

    async with httpx.AsyncClient() as client:
        url = target_url
        page_count = 1
        code_dict = defaultdict(int)
        category_dict = defaultdict(int)
        extension_dict = defaultdict(int)
        while url:
            response = await client.get(url)
            response.raise_for_status()
            page_count += 1
            data = orjson.loads(response.text)
            for entry in data.get("entry", []):
                resource = entry["resource"]
                code_dict, category_dict = extract_display_values(resource, code_dict, category_dict)
                extension_dict = extract_extension_values(resource, extension_dict)

            next_link = next((link["url"] for link in data.get("link", []) if link["relation"] == "next"), None)

            url = next_link

    parameters = {"resourceType": "Parameters", "parameter": []}
    parameters["parameter"].append({"name": "code", "resource": render_as_fhir_parameters(code_dict)})
    parameters["parameter"].append({"name": "category", "resource": render_as_fhir_parameters(category_dict)})
    parameters["parameter"].append({"name": "extension", "resource": render_as_fhir_parameters(extension_dict)})

    vocabulary_cache[target_url] = parameters

    return ORJSONResponse(content=parameters)


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
            response = await client.get(target_url, headers=headers, timeout=300)
            response.raise_for_status()
            content = orjson.loads(response.text)
            content = adjust_urls(content, forwarded_host, forwarded_proto)

            return ORJSONResponse(content=content, status_code=response.status_code)
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
