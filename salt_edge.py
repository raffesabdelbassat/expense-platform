"""Small server-side client for Salt Edge's Partners Account Information API."""

import json
import os
from datetime import date, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen


API_BASE = "https://www.saltedge.com/api/partners/v1/"
TIMEOUT_SECONDS = 20


class SaltEdgeError(RuntimeError):
    pass


def configured():
    return bool(os.getenv("SALTEDGE_APP_ID") and os.getenv("SALTEDGE_SECRET"))


def _request(url_or_path, method="GET", payload=None):
    app_id = os.getenv("SALTEDGE_APP_ID")
    secret = os.getenv("SALTEDGE_SECRET")
    if not app_id or not secret:
        raise SaltEdgeError("Bank linking is not configured. Set SALTEDGE_APP_ID and SALTEDGE_SECRET.")

    url = url_or_path if url_or_path.startswith("https://") else urljoin(API_BASE, url_or_path.lstrip("/"))
    if urlparse(url).hostname != "www.saltedge.com":
        raise SaltEdgeError("Salt Edge returned an unexpected API URL.")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url, data=body, method=method, headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
        "App-id": app_id,
        "Secret": secret,
    })
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            result = json.loads(exc.read().decode("utf-8"))
            detail = result.get("error", {}).get("message", "")
        except (ValueError, AttributeError):
            detail = ""
        raise SaltEdgeError(detail or f"Salt Edge returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise SaltEdgeError("Could not reach Salt Edge. Please try again.") from exc
    return result


def create_lead(email):
    response = _request("leads", method="POST", payload={"data": {"email": email}})
    data = response.get("data") or {}
    customer_id = data.get("customer_id")
    if not customer_id:
        raise SaltEdgeError("Salt Edge did not return a customer ID.")
    return str(customer_id)


def create_lead_session(customer_id, return_to):
    from_date = (date.today() - timedelta(days=365)).isoformat()
    response = _request("lead_sessions/create", method="POST", payload={"data": {
        "customer_id": str(customer_id),
        "allowed_countries": ["PL", "XF"],
        "consent": {
            "from_date": from_date,
            "period_days": 90,
            "scopes": ["account_details", "transactions_details"],
        },
        "attempt": {
            "from_date": from_date,
            "fetch_scopes": ["accounts", "transactions"],
            "return_to": return_to,
        },
    }})
    redirect_url = (response.get("data") or {}).get("redirect_url")
    if not redirect_url or urlparse(redirect_url).hostname != "www.saltedge.com":
        raise SaltEdgeError("Salt Edge did not return a valid bank authorization link.")
    return redirect_url


def list_connections(customer_id):
    query = urlencode({"customer_id": str(customer_id)})
    return _list_all(f"connections?{query}")


def list_accounts(connection_id):
    query = urlencode({"connection_id": str(connection_id)})
    return _list_all(f"accounts?{query}")


def list_transactions(connection_id, account_id):
    query = urlencode({"connection_id": str(connection_id), "account_id": str(account_id)})
    return _list_all(f"transactions?{query}")


def _list_all(path):
    result = []
    url = urljoin(API_BASE, path)
    for _ in range(100):
        response = _request(url)
        result.extend((response.get("data") or []))
        next_page = (response.get("meta") or {}).get("next_page")
        if not next_page:
            return result
        next_url = urljoin(API_BASE, next_page)
        if urlparse(next_url).hostname != "www.saltedge.com":
            raise SaltEdgeError("Salt Edge returned an unexpected pagination URL.")
        url = next_url
    raise SaltEdgeError("Salt Edge returned too many pages to process.")
