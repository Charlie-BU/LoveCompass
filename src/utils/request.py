import aiohttp
from typing import TypedDict


class FetchRes(TypedDict):
    status_code: int
    headers: dict[str, str]
    body: dict


async def afetch(
    url,
    method="GET",
    query_params=None,
    data=None,
    json_data=None,
    headers=None,
    timeout=30,
    raise_for_status=True,
) -> FetchRes:
    timeout_config = aiohttp.ClientTimeout(total=timeout) if timeout else None
    async with aiohttp.ClientSession(timeout=timeout_config) as session:
        async with session.request(
            method,
            url,
            params=query_params,
            data=data,
            json=json_data,
            headers=headers,
        ) as resp:
            if raise_for_status:
                resp.raise_for_status()
            try:
                return {
                    "status_code": resp.status,
                    "headers": dict(resp.headers),
                    "body": await resp.json(content_type=None),
                }
            except (aiohttp.ContentTypeError, ValueError):
                return {
                    "status_code": -1,
                    "headers": {},
                    "body": await resp.text(),
                }
