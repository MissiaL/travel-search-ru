#!/usr/bin/env python3
"""Universal HTTP client for travel search APIs."""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import ssl


ALLOWED_HOSTS = {
    "api.botclaw.ru",
    "autocomplete.travelpayouts.com",
    "www.travelpayouts.com",
    "pics.avs.io",
    "yasen.aviasales.ru",
}

BLOCKED_HEADERS = {
    "host", "authorization", "cookie", "x-forwarded-for",
    "x-real-ip", "proxy-authorization",
}


def _validate_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("https", "http"):
        raise ValueError(f"Blocked URL scheme: {parsed.scheme}. Only HTTP(S) allowed.")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(
            f"Blocked host: {parsed.hostname}. "
            f"Allowed: {', '.join(sorted(ALLOWED_HOSTS))}"
        )


def _filter_headers(headers):
    if not headers:
        return headers
    blocked = [k for k in headers if k.lower() in BLOCKED_HEADERS]
    if blocked:
        raise ValueError(f"Blocked headers: {', '.join(blocked)}")
    return headers


def make_request(method, url, params=None, body=None, headers=None):
    try:
        _validate_url(url)
        _filter_headers(headers)
        ctx = ssl.create_default_context()

        if method == "GET" and params:
            query = urllib.parse.urlencode(params, doseq=True)
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{query}"

        data = None
        if method == "POST" and body:
            data = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("User-Agent", "TravelSearchSkill/1.0")
        req.add_header("Accept", "application/json")
        if data:
            req.add_header("Content-Type", "application/json")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)

        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        result = json.loads(resp.read().decode("utf-8"))
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")[:500]
        json.dump({"error": True, "status": e.code, "message": error_body}, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        sys.exit(1)
    except Exception as e:
        json.dump({"error": True, "message": str(e)}, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="HTTP client for travel APIs")
    parser.add_argument("--method", default="GET", choices=["GET", "POST"], help="HTTP method")
    parser.add_argument("--url", required=True, help="Request URL")
    parser.add_argument("--params", default=None, help="Query params as JSON object (for GET)")
    parser.add_argument("--body", default=None, help="Request body as JSON (for POST)")
    parser.add_argument("--headers", default=None, help="Extra headers as JSON object")
    args = parser.parse_args()

    params = json.loads(args.params) if args.params else None
    body = json.loads(args.body) if args.body else None
    headers = json.loads(args.headers) if args.headers else None

    make_request(args.method, args.url, params=params, body=body, headers=headers)


if __name__ == "__main__":
    main()
