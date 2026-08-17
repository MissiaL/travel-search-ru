#!/usr/bin/env python3
"""CLI client for the travel-search MCP Streamable HTTP endpoint."""

from __future__ import annotations

import argparse
import json
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

MCP_ENDPOINT = "https://mcp.botclaw.ru/travel"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 90

COMMAND_TO_TOOL = {
    "search-tours": "search_tours",
    "search-hotels": "search_hotels",
    "get-tour-details": "get_tour_details",
    "search-flights": "search_flights",
    "flight-calendar": "get_flight_price_calendar",
    "search-trains": "search_train_tickets",
    "search-activities": "search_activities",
    "list-destinations": "list_destinations",
}

_PROTOCOL_VERSION = "2024-11-05"
_CLIENT_INFO = {"name": "travel-search-ru", "version": "2.2.0"}


class McpError(RuntimeError):
    """MCP or transport failure (safe message only)."""

    def __init__(self, category, message=None):
        self.category = category
        super(McpError, self).__init__(message or category)


def _default_port(scheme):
    if scheme == "https":
        return 443
    if scheme == "http":
        return 80
    return None


def _redirect_allowed(origin_url, target_url):
    """Return True if redirect target is allowed for the given origin."""
    origin = urllib.parse.urlparse(origin_url)
    target = urllib.parse.urlparse(target_url)
    if not target.scheme or not target.hostname:
        return False
    # Reject credential-bearing URLs (userinfo in authority).
    if target.username is not None or target.password is not None:
        return False
    production_host = "mcp.botclaw.ru"
    if origin.hostname == production_host:
        if target.scheme != "https" or target.hostname != production_host:
            return False
        target_port = target.port if target.port is not None else 443
        return target_port == 443
    origin_port = origin.port if origin.port is not None else _default_port(origin.scheme)
    target_port = target.port if target.port is not None else _default_port(target.scheme)
    return (
        target.scheme == origin.scheme
        and target.hostname == origin.hostname
        and target_port == origin_port
    )


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        configured = getattr(req, "mcp_origin", None) or req.get_full_url()
        if not _redirect_allowed(configured, newurl):
            raise McpError("redirect", "redirect rejected")
        return urllib.request.HTTPRedirectHandler.redirect_request(
            self, req, fp, code, msg, headers, newurl
        )


class McpClient(object):
    def __init__(self, endpoint=MCP_ENDPOINT, timeout=DEFAULT_TIMEOUT_SECONDS):
        self.endpoint = endpoint
        self.timeout = timeout
        self._session_id = None  # type: Optional[str]
        self._protocol_version = None  # type: Optional[str]
        self._next_id = 1
        self._ready = False
        self._ssl_context = ssl.create_default_context()
        self._opener = urllib.request.build_opener(
            _NoRedirect(),
            urllib.request.HTTPSHandler(context=self._ssl_context),
        )

    def _alloc_id(self):
        req_id = self._next_id
        self._next_id += 1
        return req_id

    def _build_request(self, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self.endpoint, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        req.add_header("User-Agent", "travel-search-ru/2.2.0")
        if self._session_id:
            req.add_header("Mcp-Session-Id", self._session_id)
        if self._protocol_version:
            req.add_header("MCP-Protocol-Version", self._protocol_version)
        req.mcp_origin = self.endpoint  # type: ignore[attr-defined]
        return req

    def _deadline_remaining(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise McpError("timeout", "timeout")
        return remaining

    def _response_socket(self, resp):
        fp = getattr(resp, "fp", None)
        if fp is None:
            return None
        raw = getattr(fp, "raw", None)
        if raw is not None:
            sock = getattr(raw, "_sock", None)
            if sock is not None:
                return sock
        return getattr(fp, "_sock", None)

    def _set_resp_timeout(self, resp, deadline):
        """Align socket inactivity timeout with remaining total deadline."""
        remaining = self._deadline_remaining(deadline)
        sock = self._response_socket(resp)
        if sock is not None:
            try:
                sock.settimeout(remaining)
            except Exception:
                pass

    def _read_some(self, resp, max_bytes, deadline=None):
        """Read up to max_bytes with bounded progress (read1-style).

        Prefer read1 so a slow trickle without a newline or full buffer cannot
        stall past the total deadline. Fall back to read() for test doubles
        and environments where read1 is unavailable.
        """
        if deadline is not None:
            self._set_resp_timeout(resp, deadline)
        try:
            chunk = self._raw_read_some(resp, max_bytes)
        except socket.timeout:
            raise McpError("timeout", "timeout")
        except Exception as exc:
            name = type(exc).__name__.lower()
            msg = str(exc).lower()
            if "timeout" in name or "timed out" in msg:
                raise McpError("timeout", "timeout")
            raise
        if not chunk:
            return b""
        return chunk

    def _raw_read_some(self, resp, max_bytes):
        """Single raw-ish read; prefer read1, then fp.read1, then read()."""
        read1 = getattr(resp, "read1", None)
        if callable(read1):
            data = read1(max_bytes)
            return data if data else b""
        fp = getattr(resp, "fp", None)
        if fp is not None:
            fp_read1 = getattr(fp, "read1", None)
            if callable(fp_read1):
                data = fp_read1(max_bytes)
                return data if data else b""
        data = resp.read(max_bytes)
        return data if data else b""

    def _read_body(self, resp, deadline=None):
        cl = resp.headers.get("Content-Length")
        if cl is not None:
            try:
                length = int(cl)
            except ValueError:
                length = None
            if length is not None and length > MAX_RESPONSE_BYTES:
                # Do not drain body bytes: a slow trickle of a declared-oversized
                # response would otherwise stall past the total deadline.
                raise McpError("response_too_large", "response too large")

        chunks = []
        total = 0
        while True:
            if deadline is not None:
                self._deadline_remaining(deadline)
            try:
                chunk = self._read_some(resp, 65536, deadline=deadline)
            except McpError:
                raise
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                raise McpError("response_too_large", "response too large")
            chunks.append(chunk)
            if deadline is not None:
                self._deadline_remaining(deadline)
        return b"".join(chunks)

    def _capture_session(self, resp):
        session = resp.headers.get("Mcp-Session-Id")
        if session:
            self._session_id = session

    def _parse_response(self, resp, expected_id, deadline):
        self._capture_session(resp)
        ctype = (resp.headers.get("Content-Type") or "").lower()

        if "text/event-stream" in ctype:
            return self._parse_sse_stream(resp, expected_id, deadline)

        raw = self._read_body(resp, deadline=deadline)

        if not raw:
            if expected_id is None:
                return None
            raise McpError("invalid_response", "empty response")

        if raw.lstrip().startswith(b"data:"):
            return self._parse_sse_bytes(raw, expected_id, deadline)

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, TypeError):
            raise McpError("invalid_response", "invalid JSON")

        return self._select_rpc(payload, expected_id)

    def _parse_sse_bytes(self, raw, expected_id, deadline):
        """Parse a fully-buffered SSE body (Content-Type not event-stream)."""
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise McpError("invalid_response", "invalid SSE")
        return self._consume_sse_text(text, expected_id, deadline, streaming=False)

    def _parse_sse_stream(self, resp, expected_id, deadline):
        """Incrementally parse SSE; return as soon as the expected id is complete."""
        total = 0
        data_lines = []  # type: List[str]
        last_msg = None  # type: Optional[Dict[str, Any]]
        # Carry incomplete trailing line across reads.
        buf = b""

        while True:
            self._deadline_remaining(deadline)
            try:
                # read1-style: return as soon as any bytes arrive so a slow
                # trickle without "\n" cannot stall past the total deadline.
                chunk = self._read_some(resp, 65536, deadline=deadline)
            except McpError:
                raise
            except Exception:
                raise McpError("transport_error", "transport error")

            if not chunk:
                # EOF — flush any pending event without trailing blank line.
                if data_lines:
                    msg = self._sse_event_from_data_lines(data_lines)
                    data_lines = []
                    selected = self._sse_try_select(msg, expected_id)
                    if selected is not None:
                        return selected
                    if isinstance(msg, dict):
                        last_msg = msg
                break

            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                raise McpError("response_too_large", "response too large")
            buf += chunk

            while True:
                nl = buf.find(b"\n")
                if nl < 0:
                    break
                line_bytes = buf[:nl]
                buf = buf[nl + 1 :]
                if line_bytes.endswith(b"\r"):
                    line_bytes = line_bytes[:-1]
                try:
                    line = line_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    raise McpError("invalid_response", "invalid SSE")

                self._deadline_remaining(deadline)

                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
                elif line.strip() == "":
                    if not data_lines:
                        continue
                    msg = self._sse_event_from_data_lines(data_lines)
                    data_lines = []
                    selected = self._sse_try_select(msg, expected_id)
                    if selected is not None:
                        return selected
                    if isinstance(msg, dict):
                        last_msg = msg
                # Comments (": ...") and other SSE fields are ignored.

        if expected_id is not None:
            raise McpError("invalid_response", "missing JSON-RPC response")
        if last_msg is not None:
            return last_msg
        raise McpError("invalid_response", "invalid SSE")

    def _sse_event_from_data_lines(self, data_lines):
        blob = "\n".join(data_lines)
        try:
            return json.loads(blob)
        except ValueError:
            raise McpError("invalid_response", "invalid SSE")

    def _sse_try_select(self, msg, expected_id):
        if expected_id is None:
            return None
        if isinstance(msg, dict) and msg.get("id") == expected_id:
            return self._select_rpc(msg, expected_id)
        return None

    def _consume_sse_text(self, text, expected_id, deadline, streaming=False):
        # Used only for fully-buffered fallback bodies.
        messages = []
        data_lines = []
        for line in text.splitlines():
            self._deadline_remaining(deadline)
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
            elif line.strip() == "":
                if data_lines:
                    messages.append(self._sse_event_from_data_lines(data_lines))
                    data_lines = []
                    if expected_id is not None:
                        selected = self._sse_try_select(messages[-1], expected_id)
                        if selected is not None:
                            return selected
        if data_lines:
            messages.append(self._sse_event_from_data_lines(data_lines))
            if expected_id is not None:
                selected = self._sse_try_select(messages[-1], expected_id)
                if selected is not None:
                    return selected

        if not messages:
            raise McpError("invalid_response", "invalid SSE")

        if expected_id is not None:
            raise McpError("invalid_response", "missing JSON-RPC response")

        last = messages[-1]
        if isinstance(last, dict):
            return last
        raise McpError("invalid_response", "invalid SSE")

    def _select_rpc(self, payload, expected_id):
        if not isinstance(payload, dict):
            raise McpError("invalid_response", "invalid JSON-RPC")
        if expected_id is not None:
            if "id" not in payload:
                raise McpError("invalid_response", "missing id")
            if payload.get("id") != expected_id:
                raise McpError("invalid_response", "id mismatch")
        if payload.get("error") is not None:
            raise McpError("mcp_error", "MCP error")
        if expected_id is not None and "result" not in payload:
            raise McpError("invalid_response", "missing result")
        return payload.get("result")

    def _post(self, payload, expected_id=None, is_notification=False):
        deadline = time.monotonic() + float(self.timeout)
        remaining = self._deadline_remaining(deadline)
        req = self._build_request(payload)
        try:
            resp = self._opener.open(req, timeout=remaining)
        except McpError:
            raise
        except urllib.error.HTTPError:
            raise McpError("http_error", "HTTP error")
        except socket.timeout:
            raise McpError("timeout", "timeout")
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.timeout):
                raise McpError("timeout", "timeout")
            reason_s = str(reason).lower() if reason is not None else ""
            if "timed out" in reason_s or "timeout" in reason_s:
                raise McpError("timeout", "timeout")
            raise McpError("network_error", "network error")
        except Exception as exc:
            name = type(exc).__name__.lower()
            msg = str(exc).lower()
            if "timeout" in name or "timed out" in msg:
                raise McpError("timeout", "timeout")
            raise McpError("transport_error", "transport error")

        try:
            if is_notification:
                self._capture_session(resp)
                try:
                    body = self._read_body(resp, deadline=deadline)
                except McpError:
                    raise
                # empty body is fine for notifications
                if not body:
                    return None
                # ignore body content for notifications
                return None
            return self._parse_response(resp, expected_id, deadline)
        finally:
            try:
                resp.close()
            except Exception:
                pass

    def _ensure_ready(self):
        if self._ready:
            return
        req_id = self._alloc_id()
        init_payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "initialize",
            "params": {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": _CLIENT_INFO,
            },
        }
        result = self._post(init_payload, expected_id=req_id)
        if not isinstance(result, dict):
            raise McpError("protocol_version", "unsupported protocol version")
        negotiated = result.get("protocolVersion")
        if negotiated != _PROTOCOL_VERSION:
            raise McpError("protocol_version", "unsupported protocol version")
        self._protocol_version = negotiated
        note = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        self._post(note, expected_id=None, is_notification=True)
        self._ready = True

    def list_tools(self):
        self._ensure_ready()
        req_id = self._alloc_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/list",
            "params": {},
        }
        result = self._post(payload, expected_id=req_id)
        if not isinstance(result, dict):
            raise McpError("invalid_response", "invalid tools/list result")
        tools = result.get("tools")
        if not isinstance(tools, list):
            raise McpError("invalid_response", "invalid tools/list result")
        return tools

    def call_tool(self, name, arguments):
        self._ensure_ready()
        req_id = self._alloc_id()
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        result = self._post(payload, expected_id=req_id)
        return _normalize_tool_result(result)


def _normalize_tool_result(result):
    if result is None:
        return {}
    if not isinstance(result, dict):
        return result
    # Tool-level error: never normalize or emit content / structuredContent.
    if result.get("isError") is True:
        raise McpError("tool_error", "tool error")
    if "structuredContent" in result and result["structuredContent"] is not None:
        return result["structuredContent"]
    content = result.get("content")
    if isinstance(content, list) and content:
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                text = item["text"].strip()
                if text and text[0] in "{[":
                    try:
                        return json.loads(text)
                    except ValueError:
                        pass
                break
    return result


def _print_json(obj):
    json.dump(obj, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")


def _fail(code, category, message):
    _print_json({"error": True, "category": category, "message": message})
    try:
        sys.stderr.write(category + "\n")
    except Exception:
        pass
    return code


def _parse_input_object(raw):
    if raw is None:
        raise ValueError("missing input")
    try:
        value = json.loads(raw)
    except ValueError:
        raise ValueError("invalid JSON")
    if not isinstance(value, dict):
        raise ValueError("input must be a JSON object")
    return value


class _HelpRequested(Exception):
    """Internal signal: emit JSON help and exit 0."""


class _QuietParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)

    def print_help(self, file=None):
        raise _HelpRequested()

    def exit(self, status=0, message=None):
        if status == 0:
            raise _HelpRequested()
        raise ValueError(message or "invalid usage")


def _emit_help():
    _print_json(
        {
            "help": True,
            "usage": (
                "python scripts/travel_search.py <command> "
                "[--input '<JSON object>']"
            ),
            "commands": list(COMMAND_TO_TOOL.keys()),
        }
    )
    return 0


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = _QuietParser(
        prog="travel_search.py",
        description="Travel search via MCP Streamable HTTP",
        add_help=True,
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list-tools", help="List CLI commands and MCP tools")

    p_desc = sub.add_parser("describe", help="Describe a CLI command MCP tool")
    p_desc.add_argument("target", help="CLI command name")

    for cli_name in COMMAND_TO_TOOL:
        p = sub.add_parser(cli_name, help="Call " + COMMAND_TO_TOOL[cli_name])
        p.add_argument("--input", required=True, help="JSON object arguments")

    try:
        args = parser.parse_args(argv)
    except _HelpRequested:
        return _emit_help()
    except ValueError:
        return _fail(2, "usage", "invalid usage")

    if not args.command:
        return _fail(2, "usage", "command required")

    try:
        if args.command == "list-tools":
            return _cmd_list_tools()
        if args.command == "describe":
            return _cmd_describe(args.target)
        if args.command in COMMAND_TO_TOOL:
            try:
                arguments = _parse_input_object(getattr(args, "input", None))
            except ValueError as exc:
                return _fail(2, "input", str(exc))
            return _cmd_call(args.command, arguments)
        return _fail(2, "usage", "unknown command")
    except McpError as exc:
        return _fail(1, exc.category, exc.category)
    except Exception:
        return _fail(1, "internal", "internal error")


def _cmd_list_tools():
    client = McpClient()
    tools = client.list_tools()
    by_name = {}  # type: Dict[str, Any]
    for t in tools:
        if isinstance(t, dict) and "name" in t:
            by_name[t["name"]] = t
    out = []  # type: List[Dict[str, Any]]
    for cli_name, mcp_name in COMMAND_TO_TOOL.items():
        tool = by_name.get(mcp_name, {})
        out.append(
            {
                "command": cli_name,
                "mcp_name": mcp_name,
                "description": tool.get("description") or "",
            }
        )
    _print_json(out)
    return 0


def _cmd_describe(cli_name):
    if cli_name not in COMMAND_TO_TOOL:
        return _fail(2, "usage", "unknown command")
    mcp_name = COMMAND_TO_TOOL[cli_name]
    client = McpClient()
    tools = client.list_tools()
    match = None
    for t in tools:
        if isinstance(t, dict) and t.get("name") == mcp_name:
            match = t
            break
    if match is None:
        return _fail(1, "not_found", "tool not found")
    _print_json(
        {
            "name": match.get("name"),
            "description": match.get("description"),
            "inputSchema": match.get("inputSchema"),
        }
    )
    return 0


def _cmd_call(cli_name, arguments):
    mcp_name = COMMAND_TO_TOOL[cli_name]
    client = McpClient()
    result = client.call_tool(mcp_name, arguments)
    _print_json(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
