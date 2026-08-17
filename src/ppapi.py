"""Minimal stdlib HTTP + OAuth2 client-credentials helpers for Power Platform admin APIs."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
USER_AGENT = "pp-env-settings-poc/0.1"

# Scopes verified against Microsoft Learn (2026-08): the BAP admin API is fronted by the
# Power Apps Service resource id, which ends in a slash - hence the double slash.
BAP_SCOPE = "https://service.powerapps.com//.default"
PPAPI_SCOPE = "https://api.powerplatform.com/.default"

RETRY_STATUS = {429, 502, 503, 504}


class ApiError(Exception):
    """Any failed call - HTTP status plus the response body, which carries the Dataverse error code."""

    def __init__(self, status: int, body: str, url: str):
        self.status = status
        self.body = body or ""
        self.url = url
        super().__init__(f"HTTP {status} for {url}: {self.body[:300]}")


class TokenProvider:
    """Caches one client-credentials token per scope."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self._tenant = tenant_id
        self._client_id = client_id
        self._secret = client_secret
        self._cache: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    def token(self, scope: str) -> str:
        with self._lock:
            hit = self._cache.get(scope)
            if hit and hit[1] > time.time() + 60:
                return hit[0]
            payload = _post_form(
                TOKEN_URL.format(tenant=self._tenant),
                {
                    "client_id": self._client_id,
                    "client_secret": self._secret,
                    "grant_type": "client_credentials",
                    "scope": scope,
                },
            )
            token = payload.get("access_token")
            if not token:
                raise ApiError(0, f"token response for {scope} contained no access_token", TOKEN_URL)
            self._cache[scope] = (token, time.time() + float(payload.get("expires_in", 3600)))
            return token


def get_json(url: str, token: str, timeout: int = 60) -> dict:
    return _send(url, token=token, timeout=timeout)


def get_paged(url: str, token: str, max_pages: int = 100) -> list[dict]:
    """Follows nextLink verbatim, tolerating the casing differences between the two APIs."""
    items: list[dict] = []
    for _ in range(max_pages):
        page = get_json(url, token)
        items.extend(page.get("value") or [])
        nxt = page.get("@odata.nextLink") or page.get("@odata.nextlink") or page.get("nextLink") or ""
        if not nxt or nxt == url:  # a server echoing the same link would loop forever
            break
        url = nxt
    return items


def _post_form(url: str, form: dict) -> dict:
    body = urllib.parse.urlencode(form).encode()
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    return _send(url, method="POST", headers=headers, data=body, timeout=30, retries=2)


def _retry_delay(retry_after: str | None, attempt: int) -> float:
    """Retry-After is legally delta-seconds or an HTTP-date; back off exponentially for the latter."""
    try:
        return min(float(retry_after), 60)
    except (TypeError, ValueError):
        return min(2**attempt, 60)


def _send(
    url: str,
    token: str | None = None,
    method: str = "GET",
    headers: dict | None = None,
    data: bytes | None = None,
    timeout: int = 60,
    retries: int = 4,
) -> dict:
    hdrs = {"Accept": "application/json", "User-Agent": USER_AGENT, **(headers or {})}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code in RETRY_STATUS and attempt < retries:
                time.sleep(_retry_delay(e.headers.get("Retry-After"), attempt))
                continue
            raise ApiError(e.code, body, url) from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            # A proxy or CDN error page lands here as a decode failure - retry, then give up cleanly.
            if attempt < retries:
                time.sleep(2**attempt)
                continue
            raise ApiError(0, str(e), url) from None
    raise ApiError(0, "retries exhausted", url)  # unreachable: the loop returns or raises


def explain(err: ApiError) -> str:
    """Maps the Dataverse errors we expect to hit into something a human can act on."""
    body = err.body
    if "0x80072560" in body or "UserNotMemberOfOrg" in body:
        return "no application user in this environment"
    if "0x80048d29" in body or "UserNotAuthorized" in body:
        return "application user lacks a security role"
    if err.status in (401, 403):
        return f"access denied (HTTP {err.status})"
    if err.status == 404:
        return "not available in this environment"
    return f"HTTP {err.status}"
