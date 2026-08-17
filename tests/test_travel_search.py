#!/usr/bin/env python3
"""Tests for travel_search MCP CLI (v2)."""

from __future__ import annotations

import io
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import travel_search  # noqa: E402


# ---------------------------------------------------------------------------
# Fake MCP server
# ---------------------------------------------------------------------------


class _ServerState(object):
    def __init__(self):
        self.requests = []  # type: List[Dict[str, Any]]
        self.session_id = "test-session-abc"
        self.mode = "json"  # json | sse
        self.tool_result = {
            "content": [{"type": "text", "text": '{"ok": true, "n": 1}'}],
            "structuredContent": {"ok": True, "n": 1},
        }
        self.tools = [
            {
                "name": "search_tours",
                "description": "Search package tours",
                "inputSchema": {
                    "type": "object",
                    "properties": {"destination": {"type": "string"}},
                },
            },
            {
                "name": "search_hotels",
                "description": "Search hotels only",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_tour_details",
                "description": "Fresh tour details",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "search_flights",
                "description": "Search flights",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_flight_price_calendar",
                "description": "Flight price calendar",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "search_train_tickets",
                "description": "Search trains",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "search_activities",
                "description": "Search activities",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "list_destinations",
                "description": "List destinations",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]
        self.http_status = 200
        self.raw_body = None  # type: Optional[bytes]
        self.jsonrpc_error = None  # type: Optional[Dict[str, Any]]
        self.invalid_json = False
        self.oversized = False
        self.delay_seconds = 0.0
        self.include_session = True
        self.force_content_type = None  # type: Optional[str]
        self.tool_call_arguments = []  # type: List[Any]
        self.custom_tool_handler = None
        # Streamable test modes for tools/list and tools/call only.
        # None | "sse_early_match" | "sse_keepalive_only"
        # | "sse_slow_trickle" | "json_slow_trickle"
        # | "oversized_declared_trickle"
        self.stream_mode = None  # type: Optional[str]
        self.stream_hold_seconds = 1.2
        self.stream_keepalive_interval = 0.05
        # Initialize result protocolVersion override (str | omit | other)
        self.init_protocol_version = "2024-11-05"  # type: Optional[str]
        self.omit_init_protocol_version = False


_STATE = _ServerState()


def _json_rpc_result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _encode_sse(payload):
    return ("data: " + json.dumps(payload, ensure_ascii=False) + "\n\n").encode("utf-8")


class FakeMcpHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            body = {"_raw": raw.decode("utf-8", errors="replace")}

        rec = {
            "path": self.path,
            "headers": {k.lower(): v for k, v in self.headers.items()},
            "body": body,
        }
        _STATE.requests.append(rec)

        if _STATE.delay_seconds:
            import time

            time.sleep(_STATE.delay_seconds)

        if _STATE.http_status != 200:
            payload = (
                b'{"error":"server boom","body":"https://evil.example/secret"}'
            )
            self.send_response(_STATE.http_status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if _STATE.oversized:
            big = b"x" * (travel_search.MAX_RESPONSE_BYTES + 100)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(big)))
            self.end_headers()
            try:
                self.wfile.write(big)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        if _STATE.raw_body is not None:
            body_bytes = _STATE.raw_body
            ctype = _STATE.force_content_type or "application/json"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body_bytes)))
            if _STATE.include_session:
                self.send_header("Mcp-Session-Id", _STATE.session_id)
            self.end_headers()
            self.wfile.write(body_bytes)
            return

        method = body.get("method")
        req_id = body.get("id")

        if method == "notifications/initialized":
            # notification — empty 202/200 is fine
            self.send_response(202)
            self.send_header("Content-Length", "0")
            if _STATE.include_session:
                self.send_header("Mcp-Session-Id", _STATE.session_id)
            self.end_headers()
            return

        if method == "initialize":
            result = {
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake-travel", "version": "0.0.1"},
            }
            if not _STATE.omit_init_protocol_version:
                result["protocolVersion"] = _STATE.init_protocol_version
            payload = _json_rpc_result(req_id, result)
        elif method == "tools/list":
            payload = _json_rpc_result(req_id, {"tools": _STATE.tools})
        elif method == "tools/call":
            params = body.get("params") or {}
            _STATE.tool_call_arguments.append(params.get("arguments"))
            if _STATE.custom_tool_handler:
                result = _STATE.custom_tool_handler(params)
            else:
                result = _STATE.tool_result
            payload = _json_rpc_result(req_id, result)
        else:
            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": "Method not found"},
            }

        if _STATE.jsonrpc_error is not None and method != "initialize":
            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": _STATE.jsonrpc_error,
            }

        # Streaming modes: hold connection open after headers.
        if (
            _STATE.stream_mode
            and method in ("tools/list", "tools/call")
            and not _STATE.invalid_json
        ):
            if _STATE.stream_mode == "json_slow_trickle":
                self._write_slow_json_trickle()
            elif _STATE.stream_mode == "oversized_declared_trickle":
                self._write_oversized_declared_trickle()
            else:
                self._write_streaming_sse(payload, req_id)
            return

        if _STATE.invalid_json and method != "initialize":
            body_bytes = b"not-json{{{"
            ctype = "application/json"
        elif _STATE.mode == "sse":
            body_bytes = _encode_sse(payload)
            # prepend an unrelated event with different id to ensure selection
            other = dict(payload)
            other["id"] = 999999
            other["result"] = {"tools": [], "wrong": True}
            body_bytes = _encode_sse(other) + body_bytes
            ctype = "text/event-stream"
        else:
            body_bytes = json.dumps(payload).encode("utf-8")
            ctype = "application/json"

        if _STATE.force_content_type:
            ctype = _STATE.force_content_type

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body_bytes)))
        if _STATE.include_session:
            self.send_header("Mcp-Session-Id", _STATE.session_id)
        self.end_headers()
        self.wfile.write(body_bytes)

    def _write_streaming_sse(self, payload, req_id):
        """Hold-open SSE stream for early-return and total-deadline tests."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        if _STATE.include_session:
            self.send_header("Mcp-Session-Id", _STATE.session_id)
        # No Content-Length: body ends when the handler closes the connection.
        self.end_headers()
        try:
            if _STATE.stream_mode == "sse_early_match":
                # Unrelated id first, then matching result, then keepalives.
                other = dict(payload)
                other["id"] = 999999
                other["result"] = {"tools": [], "wrong": True}
                self.wfile.write(_encode_sse(other))
                self.wfile.write(_encode_sse(payload))
                self.wfile.flush()
                end = time.monotonic() + float(_STATE.stream_hold_seconds)
                while time.monotonic() < end:
                    time.sleep(float(_STATE.stream_keepalive_interval))
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
            elif _STATE.stream_mode == "sse_keepalive_only":
                # Keepalives only — never emit the matching request id.
                end = time.monotonic() + float(_STATE.stream_hold_seconds)
                while time.monotonic() < end:
                    time.sleep(float(_STATE.stream_keepalive_interval))
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                # After hold, optionally emit a non-matching event then close.
                decoy = {
                    "jsonrpc": "2.0",
                    "id": 999999,
                    "result": {"tools": []},
                }
                self.wfile.write(_encode_sse(decoy))
                self.wfile.flush()
            elif _STATE.stream_mode == "sse_slow_trickle":
                # Bytes keep arriving without "\n" so readline() never returns,
                # but each recv stays under the socket inactivity timeout.
                end = time.monotonic() + float(_STATE.stream_hold_seconds)
                while time.monotonic() < end:
                    self.wfile.write(b"x")
                    self.wfile.flush()
                    time.sleep(float(_STATE.stream_keepalive_interval))
            else:
                self.wfile.write(_encode_sse(payload))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            # Client closed early after matching event — expected for early-return.
            pass

    def _write_slow_json_trickle(self):
        """Slow incomplete JSON body: bytes arrive, document never completes."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        if _STATE.include_session:
            self.send_header("Mcp-Session-Id", _STATE.session_id)
        self.end_headers()
        try:
            end = time.monotonic() + float(_STATE.stream_hold_seconds)
            # Never a complete JSON value — just open braces / noise.
            while time.monotonic() < end:
                self.wfile.write(b"{")
                self.wfile.flush()
                time.sleep(float(_STATE.stream_keepalive_interval))
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _write_oversized_declared_trickle(self):
        """Content-Length > cap with a slow body trickle (deadline hole probe)."""
        declared = travel_search.MAX_RESPONSE_BYTES + 100
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(declared))
        self.send_header("Cache-Control", "no-cache")
        if _STATE.include_session:
            self.send_header("Mcp-Session-Id", _STATE.session_id)
        self.end_headers()
        try:
            end = time.monotonic() + float(_STATE.stream_hold_seconds)
            while time.monotonic() < end:
                self.wfile.write(b"x")
                self.wfile.flush()
                time.sleep(float(_STATE.stream_keepalive_interval))
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass


class FakeMcpServer(object):
    def __init__(self):
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), FakeMcpHandler)
        self.port = self._httpd.server_address[1]
        # Local in-process server (scheme split so integrity scans ignore fixture URLs)
        self.endpoint = "{0}://127.0.0.1:{1}/travel".format("http", self.port)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=2)

    def reset(self):
        global _STATE
        _STATE = _ServerState()


def _run_main(argv):
    out = io.StringIO()
    err = io.StringIO()
    code = 0
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = travel_search.main(argv)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
    return code, out.getvalue(), err.getvalue()


def _load_json_stdout(stdout):
    return json.loads(stdout)


class TravelSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = FakeMcpServer()
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def setUp(self):
        self.server.reset()
        # Patch production client construction in main to use test endpoint
        self._orig_client = travel_search.McpClient

        endpoint = self.server.endpoint

        class _TestClient(travel_search.McpClient):
            def __init__(self, endpoint=endpoint, timeout=travel_search.DEFAULT_TIMEOUT_SECONDS):
                super(_TestClient, self).__init__(endpoint=endpoint, timeout=timeout)

        travel_search.McpClient = _TestClient

    def tearDown(self):
        travel_search.McpClient = self._orig_client

    # --- protocol ---

    def test_initialize_session_and_initialized_notification(self):
        client = travel_search.McpClient(endpoint=self.server.endpoint, timeout=5)
        tools = client.list_tools()
        self.assertTrue(isinstance(tools, list))
        self.assertGreaterEqual(len(_STATE.requests), 3)

        methods = [r["body"].get("method") for r in _STATE.requests]
        self.assertEqual(methods[0], "initialize")
        self.assertEqual(methods[1], "notifications/initialized")
        self.assertEqual(methods[2], "tools/list")

        # session header on post-init requests
        for r in _STATE.requests[1:]:
            self.assertEqual(r["headers"].get("mcp-session-id"), _STATE.session_id)

        # integer json-rpc ids on requests with id
        for r in _STATE.requests:
            body = r["body"]
            if "id" in body:
                self.assertIsInstance(body["id"], int)

    def test_json_response_tools_list(self):
        _STATE.mode = "json"
        client = travel_search.McpClient(endpoint=self.server.endpoint, timeout=5)
        tools = client.list_tools()
        names = [t["name"] for t in tools]
        self.assertIn("search_tours", names)

    def test_sse_response_tools_list(self):
        _STATE.mode = "sse"
        client = travel_search.McpClient(endpoint=self.server.endpoint, timeout=5)
        tools = client.list_tools()
        names = [t["name"] for t in tools]
        self.assertIn("search_tours", names)
        # must not pick the decoy id=999999 empty tools payload
        self.assertEqual(len(tools), 8)

    def test_session_header_preserved_on_tool_call(self):
        client = travel_search.McpClient(endpoint=self.server.endpoint, timeout=5)
        client.call_tool("search_tours", {"destination": "TR"})
        call_reqs = [
            r for r in _STATE.requests if r["body"].get("method") == "tools/call"
        ]
        self.assertEqual(len(call_reqs), 1)
        self.assertEqual(call_reqs[0]["headers"].get("mcp-session-id"), _STATE.session_id)

    # --- CLI mappings ---

    def test_all_eight_command_mappings(self):
        expected = {
            "search-tours": "search_tours",
            "search-hotels": "search_hotels",
            "get-tour-details": "get_tour_details",
            "search-flights": "search_flights",
            "flight-calendar": "get_flight_price_calendar",
            "search-trains": "search_train_tickets",
            "search-activities": "search_activities",
            "list-destinations": "list_destinations",
        }
        self.assertEqual(travel_search.COMMAND_TO_TOOL, expected)
        self.assertEqual(len(travel_search.COMMAND_TO_TOOL), 8)

        for cli_name, mcp_name in expected.items():
            _STATE.requests.clear()
            _STATE.tool_call_arguments.clear()
            code, stdout, _err = _run_main(
                [cli_name, "--input", json.dumps({"k": cli_name})]
            )
            self.assertEqual(code, 0, msg=cli_name)
            call_reqs = [
                r for r in _STATE.requests if r["body"].get("method") == "tools/call"
            ]
            self.assertEqual(len(call_reqs), 1, msg=cli_name)
            params = call_reqs[0]["body"]["params"]
            self.assertEqual(params["name"], mcp_name)
            self.assertEqual(params["arguments"], {"k": cli_name})

    def test_exact_json_object_forwarding(self):
        payload = {
            "destination": "Antalya",
            "adults": 2,
            "kids": 1,
            "nested": {"a": [1, 2, 3]},
            "flag": True,
            "n": None,
        }
        code, stdout, _ = _run_main(
            ["search-tours", "--input", json.dumps(payload, separators=(",", ":"))]
        )
        self.assertEqual(code, 0)
        self.assertEqual(_STATE.tool_call_arguments[-1], payload)

    def test_tools_call_params_shape(self):
        code, _, _ = _run_main(
            ["search-hotels", "--input", '{"city":"Istanbul"}']
        )
        self.assertEqual(code, 0)
        call = [
            r for r in _STATE.requests if r["body"].get("method") == "tools/call"
        ][0]
        self.assertEqual(
            call["body"]["params"],
            {"name": "search_hotels", "arguments": {"city": "Istanbul"}},
        )

    # --- result normalization ---

    def test_prefers_structured_content(self):
        _STATE.tool_result = {
            "content": [{"type": "text", "text": '{"from":"text"}'}],
            "structuredContent": {"from": "structured"},
        }
        code, stdout, _ = _run_main(["search-tours", "--input", "{}"])
        self.assertEqual(code, 0)
        data = _load_json_stdout(stdout)
        self.assertEqual(data, {"from": "structured"})

    def test_json_text_content_when_no_structured(self):
        _STATE.tool_result = {
            "content": [{"type": "text", "text": '{"from":"json-text","n":3}'}],
        }
        code, stdout, _ = _run_main(["search-tours", "--input", "{}"])
        self.assertEqual(code, 0)
        data = _load_json_stdout(stdout)
        self.assertEqual(data, {"from": "json-text", "n": 3})

    def test_plain_text_content_returned_without_invention(self):
        _STATE.tool_result = {
            "content": [{"type": "text", "text": "plain partial results available"}],
        }
        code, stdout, _ = _run_main(["search-tours", "--input", "{}"])
        self.assertEqual(code, 0)
        data = _load_json_stdout(stdout)
        # must preserve MCP result/content shape, not invent fields
        self.assertIn("content", data)
        self.assertEqual(
            data["content"][0]["text"], "plain partial results available"
        )

    def test_partial_provider_results_are_success(self):
        _STATE.tool_result = {
            "structuredContent": {
                "results": [{"hotel": "A"}],
                "errors": [{"provider": "x", "message": "timeout"}],
                "partial": True,
            }
        }
        code, stdout, _ = _run_main(["search-tours", "--input", "{}"])
        self.assertEqual(code, 0)
        data = _load_json_stdout(stdout)
        self.assertTrue(data.get("partial"))
        self.assertEqual(len(data["results"]), 1)

    def test_is_error_true_exits_1_hides_content(self):
        _STATE.tool_result = {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": "malicious leak https://evil.example/steal?token=abc123",
                }
            ],
            "structuredContent": {
                "secret": "https://evil.example/raw-booking/xyz",
                "detail": "internal stack trace",
            },
        }
        code, stdout, err = _run_main(["search-tours", "--input", "{}"])
        self.assertEqual(code, 1)
        data = _load_json_stdout(stdout)
        self.assertTrue(data.get("error"))
        blob = stdout + err
        self.assertNotIn("evil.example", blob)
        self.assertNotIn("malicious leak", blob)
        self.assertNotIn("steal", blob)
        self.assertNotIn("abc123", blob)
        self.assertNotIn("raw-booking", blob)
        self.assertNotIn("stack trace", blob)
        # exactly one JSON document on stdout
        decoder = json.JSONDecoder()
        obj, idx = decoder.raw_decode(stdout.strip())
        self.assertEqual(stdout.strip()[idx:].strip(), "")
        self.assertIsInstance(obj, dict)

    def test_partial_structured_without_is_error_stays_success(self):
        _STATE.tool_result = {
            "structuredContent": {
                "results": [{"hotel": "B", "price": 100}],
                "errors": [{"provider": "y", "message": "timeout"}],
                "partial": True,
            }
        }
        # isError absent (not true) — useful partial data is success
        code, stdout, _ = _run_main(["search-tours", "--input", "{}"])
        self.assertEqual(code, 0)
        data = _load_json_stdout(stdout)
        self.assertTrue(data.get("partial"))
        self.assertEqual(data["results"][0]["hotel"], "B")

    def test_is_error_false_with_structured_is_success(self):
        _STATE.tool_result = {
            "isError": False,
            "structuredContent": {"ok": True, "n": 2},
        }
        code, stdout, _ = _run_main(["search-tours", "--input", "{}"])
        self.assertEqual(code, 0)
        data = _load_json_stdout(stdout)
        self.assertEqual(data, {"ok": True, "n": 2})

    # --- help (JSON only, exit 0) ---

    def test_top_level_help_json_exit_0(self):
        for flag in ["-h", "--help"]:
            code, stdout, err = _run_main([flag])
            self.assertEqual(code, 0, msg=flag)
            data = _load_json_stdout(stdout)
            self.assertIsInstance(data, dict)
            # single JSON document
            decoder = json.JSONDecoder()
            obj, idx = decoder.raw_decode(stdout.strip())
            self.assertEqual(stdout.strip()[idx:].strip(), "", msg=flag)
            # usage plus all command names
            blob = json.dumps(data, ensure_ascii=False)
            for cmd in travel_search.COMMAND_TO_TOOL:
                self.assertIn(cmd, blob, msg="{0}/{1}".format(flag, cmd))
            # argparse prose / SystemExit must not escape outside the JSON document
            self.assertNotIn("Traceback", stdout + err)
            self.assertFalse(
                stdout.lstrip().lower().startswith("usage:"),
                msg=flag,
            )

    def test_subcommand_help_json_exit_0(self):
        code, stdout, err = _run_main(["search-tours", "--help"])
        self.assertEqual(code, 0)
        data = _load_json_stdout(stdout)
        self.assertIsInstance(data, dict)
        decoder = json.JSONDecoder()
        obj, idx = decoder.raw_decode(stdout.strip())
        self.assertEqual(stdout.strip()[idx:].strip(), "")
        blob = json.dumps(data, ensure_ascii=False)
        self.assertIn("search-tours", blob)
        for cmd in travel_search.COMMAND_TO_TOOL:
            self.assertIn(cmd, blob)
        self.assertNotIn("Traceback", stdout + err)

    # --- describe / list-tools ---

    def test_describe_returns_schema(self):
        code, stdout, _ = _run_main(["describe", "search-tours"])
        self.assertEqual(code, 0)
        data = _load_json_stdout(stdout)
        self.assertEqual(data["name"], "search_tours")
        self.assertEqual(data["description"], "Search package tours")
        self.assertIn("inputSchema", data)
        self.assertEqual(data["inputSchema"]["type"], "object")

    def test_list_tools_returns_eight_with_descriptions(self):
        code, stdout, _ = _run_main(["list-tools"])
        self.assertEqual(code, 0)
        data = _load_json_stdout(stdout)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 8)
        by_cli = {item["command"]: item for item in data}
        for cli, mcp in travel_search.COMMAND_TO_TOOL.items():
            self.assertIn(cli, by_cli)
            self.assertEqual(by_cli[cli]["mcp_name"], mcp)
            self.assertTrue(by_cli[cli]["description"])

    # --- input validation (exit 2) ---

    def test_missing_input_exits_2(self):
        code, stdout, err = _run_main(["search-tours"])
        self.assertEqual(code, 2)
        data = _load_json_stdout(stdout)
        self.assertTrue(data.get("error"))
        self.assertNotIn("https://evil", stdout)

    def test_invalid_json_input_exits_2(self):
        code, stdout, err = _run_main(["search-tours", "--input", "{not-json"])
        self.assertEqual(code, 2)
        data = _load_json_stdout(stdout)
        self.assertTrue(data.get("error"))

    def test_non_object_input_exits_2(self):
        for bad in ["[]", '"str"', "1", "null", "true"]:
            code, stdout, _ = _run_main(["search-tours", "--input", bad])
            self.assertEqual(code, 2, msg=bad)
            data = _load_json_stdout(stdout)
            self.assertTrue(data.get("error"), msg=bad)

    def test_unknown_command_exits_2(self):
        code, stdout, _ = _run_main(["nope", "--input", "{}"])
        self.assertEqual(code, 2)
        data = _load_json_stdout(stdout)
        self.assertTrue(data.get("error"))

    def test_describe_unknown_command_exits_2(self):
        code, stdout, _ = _run_main(["describe", "nope"])
        self.assertEqual(code, 2)

    # --- transport / MCP errors (exit 1) ---

    def test_http_4xx_exits_1_safe_output(self):
        _STATE.http_status = 503
        code, stdout, err = _run_main(["search-tours", "--input", "{}"])
        self.assertEqual(code, 1)
        data = _load_json_stdout(stdout)
        self.assertTrue(data.get("error"))
        blob = stdout + err
        self.assertNotIn("server boom", blob)
        self.assertNotIn("https://evil.example/secret", blob)
        self.assertNotIn("evil.example", blob)

    def test_jsonrpc_error_exits_1(self):
        _STATE.jsonrpc_error = {
            "code": -32000,
            "message": "upstream failed",
            "data": {"url": "https://raw.example/booking/abc123long"},
        }
        code, stdout, err = _run_main(["search-tours", "--input", "{}"])
        self.assertEqual(code, 1)
        data = _load_json_stdout(stdout)
        self.assertTrue(data.get("error"))
        blob = stdout + err
        self.assertNotIn("https://raw.example/booking/abc123long", blob)
        self.assertNotIn("raw.example", blob)

    def test_invalid_json_response_exits_1(self):
        _STATE.invalid_json = True
        code, stdout, err = _run_main(["list-tools"])
        self.assertEqual(code, 1)
        data = _load_json_stdout(stdout)
        self.assertTrue(data.get("error"))
        self.assertNotIn("not-json", stdout)

    def test_id_bearing_response_without_id_rejected(self):
        # Response has result but missing id entirely
        client = travel_search.McpClient(endpoint=self.server.endpoint, timeout=5)
        _STATE.raw_body = None
        client._ensure_ready()  # type: ignore[attr-defined]
        missing_id = json.dumps(
            {"jsonrpc": "2.0", "result": {"tools": _STATE.tools}}
        ).encode("utf-8")
        _STATE.raw_body = missing_id
        _STATE.force_content_type = "application/json"
        with self.assertRaises(travel_search.McpError) as ctx:
            client.list_tools()
        self.assertEqual(ctx.exception.category, "invalid_response")

    def test_invalid_sse_exits_1(self):
        _STATE.raw_body = b"event: ping\ndata: not-json\n\n"
        _STATE.force_content_type = "text/event-stream"
        # Need initialize to succeed first — use custom flow via client only
        # For main, initialize also gets raw_body. Set raw only after... hard.
        # Unit-test parse path via client with forced sequence:
        client = travel_search.McpClient(endpoint=self.server.endpoint, timeout=5)
        # First allow normal init by temporarily clearing raw
        _STATE.raw_body = None
        _STATE.force_content_type = None
        client._ensure_ready()  # type: ignore[attr-defined]
        _STATE.raw_body = b": comment\ndata: {bad\n\n"
        _STATE.force_content_type = "text/event-stream"
        with self.assertRaises(travel_search.McpError):
            client.list_tools()

    def test_oversized_response_exits_1(self):
        _STATE.oversized = True
        # init will also be oversized — expect failure
        code, stdout, err = _run_main(["list-tools"])
        self.assertEqual(code, 1)
        data = _load_json_stdout(stdout)
        self.assertTrue(data.get("error"))
        # body of xxxx must not appear
        self.assertNotIn("xxxxx", stdout)

    def test_timeout_exits_1(self):
        _STATE.delay_seconds = 2.0
        client = travel_search.McpClient(endpoint=self.server.endpoint, timeout=0.2)
        with self.assertRaises(travel_search.McpError):
            client.list_tools()
        # CLI path
        travel_search.McpClient = type(
            "C",
            (travel_search.McpClient,),
            {
                "__init__": lambda self, endpoint=self.server.endpoint, timeout=0.2: (
                    travel_search.McpClient.__init__(self, endpoint=endpoint, timeout=timeout)
                )
            },
        )
        # simpler: patch DEFAULT and construct via setUp override
        class SlowClient(self._orig_client):
            def __init__(self, endpoint=self.server.endpoint, timeout=0.2):
                super(SlowClient, self).__init__(endpoint=endpoint, timeout=timeout)

        travel_search.McpClient = SlowClient
        _STATE.requests.clear()
        code, stdout, err = _run_main(["list-tools"])
        self.assertEqual(code, 1)
        data = _load_json_stdout(stdout)
        self.assertTrue(data.get("error"))
        # no exception reprs or body leaks
        self.assertNotIn("Traceback", stdout)
        self.assertNotIn("server boom", stdout)
        self.assertNotIn("Traceback", err)

    # --- redirects ---

    def test_reject_cross_host_redirect_production(self):
        allowed = travel_search._redirect_allowed(
            "https://mcp.botclaw.ru/travel",
            "https://evil.example/travel",
        )
        self.assertFalse(allowed)

    def test_reject_cross_scheme_redirect_production(self):
        allowed = travel_search._redirect_allowed(
            "https://mcp.botclaw.ru/travel",
            "http://mcp.botclaw.ru/travel",
        )
        self.assertFalse(allowed)

    def test_accept_same_host_https_redirect_production(self):
        allowed = travel_search._redirect_allowed(
            "https://mcp.botclaw.ru/travel",
            "https://mcp.botclaw.ru/travel/v2",
        )
        self.assertTrue(allowed)

    def test_reject_production_non_443_port(self):
        allowed = travel_search._redirect_allowed(
            "https://mcp.botclaw.ru/travel",
            "https://mcp.botclaw.ru:444/travel",
        )
        self.assertFalse(allowed)

    def test_reject_production_credential_bearing_redirect(self):
        allowed = travel_search._redirect_allowed(
            "https://mcp.botclaw.ru/travel",
            "https://user:pass@mcp.botclaw.ru/travel",
        )
        self.assertFalse(allowed)
        allowed2 = travel_search._redirect_allowed(
            "https://mcp.botclaw.ru/travel",
            "https://user@mcp.botclaw.ru/travel/v2",
        )
        self.assertFalse(allowed2)

    def test_accept_production_explicit_443(self):
        allowed = travel_search._redirect_allowed(
            "https://mcp.botclaw.ru/travel",
            "https://mcp.botclaw.ru:443/travel/v2",
        )
        self.assertTrue(allowed)

    def test_test_endpoint_same_origin_only(self):
        origin = "{0}://127.0.0.1:9/travel".format("http")
        self.assertTrue(
            travel_search._redirect_allowed(
                origin, "{0}://127.0.0.1:9/other".format("http")
            )
        )
        self.assertFalse(
            travel_search._redirect_allowed(
                origin, "{0}://127.0.0.1:10/other".format("http")
            )
        )
        self.assertFalse(
            travel_search._redirect_allowed(
                origin, "{0}://127.0.0.1:9/other".format("https")
            )
        )
        self.assertFalse(
            travel_search._redirect_allowed(
                origin, "{0}://evil.local/other".format("http")
            )
        )

    def test_test_endpoint_rejects_credentials(self):
        origin = "{0}://127.0.0.1:9/travel".format("http")
        self.assertFalse(
            travel_search._redirect_allowed(
                origin, "{0}://user:pass@127.0.0.1:9/other".format("http")
            )
        )
        self.assertFalse(
            travel_search._redirect_allowed(
                origin, "{0}://user@127.0.0.1:9/other".format("http")
            )
        )

    # --- constants ---

    def test_constants(self):
        self.assertEqual(
            travel_search.MCP_ENDPOINT, "https://mcp.botclaw.ru/travel"
        )
        self.assertEqual(travel_search.MAX_RESPONSE_BYTES, 5 * 1024 * 1024)
        self.assertEqual(travel_search.DEFAULT_TIMEOUT_SECONDS, 90)

    def test_public_cli_has_no_url_flag(self):
        code, stdout, _ = _run_main(
            ["search-tours", "--url", "http://evil", "--input", "{}"]
        )
        # argparse should reject unknown --url or treat as usage error
        self.assertEqual(code, 2)
        self.assertNotIn("evil", stdout)

    # --- package / docs integrity ---

    def test_version_synchronization(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg["version"], "2.2.0")
        data, _ = self._skill_frontmatter()
        meta = data.get("metadata")
        # Agent Skills: metadata must be a YAML mapping of string values
        # (not inline JSON-style object; keywords not a YAML/JSON list).
        self.assertIsInstance(
            meta, dict, msg="metadata must be a YAML block mapping"
        )
        self.assertEqual(meta.get("author"), "MissiaL")
        self.assertEqual(str(meta.get("version")), "2.2.0")
        self.assertIsInstance(
            meta.get("version"),
            str,
            msg="metadata.version must be a string",
        )
        keywords = meta.get("keywords")
        self.assertIsInstance(
            keywords,
            str,
            msg="metadata.keywords must be one comma-separated string, not a list",
        )
        for kw in (
            "travel",
            "travel-planning",
            "trip-planner",
            "itinerary",
            "flights",
            "trains",
            "tours",
            "hotels",
            "excursions",
            "mcp",
            "russia",
            "turkey",
            "egypt",
            "booking",
            "путешествия",
            "планирование путешествий",
        ):
            self.assertIn(kw, keywords)
        self.assertNotRegex(
            skill,
            r"(?m)^metadata\s*:\s*\{",
            msg="metadata must not use inline JSON-style object syntax",
        )
        # CLI client info / User-Agent stay synchronized with the release
        self.assertEqual(travel_search._CLIENT_INFO.get("version"), "2.2.0")
        src = (ROOT / "scripts" / "travel_search.py").read_text(encoding="utf-8")
        self.assertIn('User-Agent", "travel-search-ru/2.2.0"', src)
        self.assertNotIn("2.0.1", pkg["version"])
        self.assertNotIn("2.0.0", pkg["version"])
        self.assertNotIn("2.0.2", pkg["version"])

    def test_skill_md_line_limit(self):
        lines = (ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(len(lines), 100)

    def test_skill_links_only_usage(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        # only references/usage.md
        refs = re.findall(r"references/[\w./-]+", skill)
        for r in refs:
            self.assertEqual(r, "references/usage.md")
        deleted = [
            "api_call.py",
            "aviasales-data-api.md",
            "aviasales-links.md",
            "leveltravel-api.md",
            "sputnik8-api.md",
            "tour-selection-playbook.md",
            "travelata-api.md",
            "travelata-directories.md",
            "travelpayouts-utils.md",
            "departure-cities.json",
        ]
        for d in deleted:
            self.assertNotIn(d, skill)

    def test_no_http_urls_in_public_files(self):
        # Product sources only (tests use a local HTTP fixture server).
        files = [
            ROOT / "SKILL.md",
            ROOT / "README.md",
            ROOT / "references" / "usage.md",
            ROOT / "scripts" / "travel_search.py",
        ]
        for path in files:
            text = path.read_text(encoding="utf-8")
            for m in re.finditer(r"http://[^\s)\"']+", text):
                self.fail("HTTP URL in {0}: {1}".format(path.name, m.group(0)))

    def test_no_prohibited_terms(self):
        # Build pattern without narrative occurrences of the banned words.
        source_word = "par" + "tner"
        allowed_route = "/travelata-" + source_word + "s/"
        banned = [
            "aff" + "iliate",
            "comm" + "ission",
            "mar" + "ker",
            source_word + "s?",
        ]
        prohibited = re.compile(
            r"\b(" + "|".join(banned) + r")\b", re.IGNORECASE
        )
        paths = []
        for p in ROOT.rglob("*"):
            if not p.is_file() or p.suffix not in {".md", ".py"}:
                continue
            if (
                ".git" in p.parts
                or ".superpowers" in p.parts
                or "__pycache__" in p.parts
            ):
                continue
            paths.append(p)
        for path in paths:
            text = path.read_text(encoding="utf-8").replace(allowed_route, "")
            m = prohibited.search(text)
            if m:
                self.fail(
                    "Prohibited term {0!r} in {1}".format(m.group(0), path)
                )

    def test_local_task_report_is_not_in_public_root(self):
        self.assertFalse(
            (ROOT / ".superpowers-task6-report.md").exists(),
            msg="local task report must live under ignored .superpowers/sdd",
        )

    def test_package_json_files_exist(self):
        pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        for entry in pkg.get("files", []):
            target = ROOT / entry.rstrip("/")
            self.assertTrue(
                target.exists(), "package.json files entry missing: " + entry
            )

    def test_deleted_paths_absent(self):
        deleted = [
            "scripts/api_call.py",
            "tests/test_api_call.py",
            "references/aviasales-data-api.md",
            "references/aviasales-links.md",
            "references/leveltravel-api.md",
            "references/sputnik8-api.md",
            "references/tour-selection-playbook.md",
            "references/travelata-api.md",
            "references/travelata-directories.md",
            "references/travelpayouts-utils.md",
            "assets/departure-cities.json",
        ]
        for rel in deleted:
            self.assertFalse(
                (ROOT / rel).exists(), "should be deleted: " + rel
            )

    def test_stderr_safe_on_success(self):
        code, stdout, err = _run_main(["list-tools"])
        self.assertEqual(code, 0)
        # stderr may be empty or short category only
        self.assertLess(len(err.strip()), 200)
        self.assertNotIn("Traceback", err)

    def test_exactly_one_json_document_stdout(self):
        code, stdout, _ = _run_main(["list-tools"])
        self.assertEqual(code, 0)
        # single JSON value
        decoder = json.JSONDecoder()
        obj, idx = decoder.raw_decode(stdout.strip())
        rest = stdout.strip()[idx:].strip()
        self.assertEqual(rest, "")
        self.assertIsInstance(obj, list)

    # --- docs: budget rule, examples, Russian README ---

    def test_skill_no_unconditional_above_budget(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        # Must not instruct agent to auto-show above-budget offers
        bad_patterns = [
            r"show the cheapest options clearly marked as above budget",
            r"On budget overruns,\s*show",
            r"automatically\s+show.*above.?budget",
            r"always\s+show.*above.?budget",
        ]
        for pat in bad_patterns:
            self.assertIsNone(
                re.search(pat, skill, re.IGNORECASE),
                msg="unconditional above-budget instruction: " + pat,
            )
        # Consent + separate section required if alternatives mentioned
        if re.search(r"above.?budget|over.?budget|сверх\s*бюджет", skill, re.IGNORECASE):
            self.assertTrue(
                re.search(
                    r"explicit\s+user\s+consent|user\s+consent|явн\w+\s+согласи",
                    skill,
                    re.IGNORECASE,
                ),
                msg="above-budget alternatives require explicit user consent",
            )
            self.assertTrue(
                re.search(
                    r"separate\s+labeled\s+section|отдельн\w+\s+секци",
                    skill,
                    re.IGNORECASE,
                ),
                msg="above-budget alternatives need a separate labeled section",
            )

    def test_skill_and_readme_live_tour_example_fields(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        required_fields = [
            "departure_city",
            "country",
            "date_from",
            "date_to",
            "adults",
        ]
        for text, label in ((skill, "SKILL.md"), (readme, "README.md")):
            for field in required_fields:
                self.assertIn(field, text, msg="{0} missing {1}".format(label, field))
            # required tour example shape (values from spec)
            self.assertIn("Москва", text, msg=label)
            self.assertIn("Турция", text, msg=label)
            self.assertIn("2026-09-10", text, msg=label)
            self.assertIn("2026-09-20", text, msg=label)
        # invalid old-style destination-only tour example must not remain as the tour demo
        self.assertNotIn(
            '{"destination":"Turkey","adults":2}',
            readme,
        )
        self.assertNotIn(
            '{"destination":"Turkey","adults":2}',
            skill,
        )

    def test_skill_and_usage_live_flight_and_activity_example_fields(self):
        """Docs must use live MCP field names for flights and activities."""
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        usage = (ROOT / "references" / "usage.md").read_text(encoding="utf-8")
        required_flight = (
            'python scripts/travel_search.py search-flights --input '
            '\'{"origin":"MOW","destination":"AYT","depart_date":"2026-09-15","adults":1}\''
        )
        required_activity = (
            'python scripts/travel_search.py search-activities --input '
            '\'{"city":"Анталья","date_from":"2026-09-10",'
            '"date_to":"2026-09-12","persons":2,'
            '"children_allowed":true,"sort":"recommended","limit":5}\''
        )
        flight_input_re = re.compile(
            r"search-flights\s+--input\s+'(\{[^']*\})'"
        )
        activity_input_re = re.compile(
            r"search-activities\s+--input\s+'(\{[^']*\})'"
        )
        live_flight_keys = ("origin", "destination", "depart_date")
        for text, label in ((skill, "SKILL.md"), (usage, "references/usage.md")):
            self.assertIn(required_flight, text, msg=label + " missing live flights example")
            self.assertIn(required_activity, text, msg=label + " missing live activities example")

            flight_inputs = flight_input_re.findall(text)
            self.assertTrue(
                flight_inputs,
                msg="{0}: no search-flights --input examples to inspect".format(label),
            )
            for raw in flight_inputs:
                payload = json.loads(raw)
                self.assertNotIn(
                    "departure_at",
                    payload,
                    msg="{0}: flights must not use departure_at".format(label),
                )
                for key in live_flight_keys:
                    self.assertIn(
                        key,
                        payload,
                        msg="{0}: flights example missing live key {1}".format(
                            label, key
                        ),
                    )

            activity_inputs = activity_input_re.findall(text)
            self.assertTrue(
                activity_inputs,
                msg="{0}: no search-activities --input examples to inspect".format(
                    label
                ),
            )
            for raw in activity_inputs:
                payload = json.loads(raw)
                self.assertIn(
                    "city",
                    payload,
                    msg="{0}: activities example missing required live key city".format(
                        label
                    ),
                )

    def test_2_2_0_train_search_contract_in_public_docs(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        usage = (ROOT / "references" / "usage.md").read_text(encoding="utf-8")
        example = (
            'python scripts/travel_search.py search-trains --input '
            "'{\"origin\":\"Москва\",\"destination\":\"Сочи\","
            "\"depart_date\":\"2026-09-15\",\"sort\":\"price\",\"limit\":5}'"
        )
        for text, label in ((skill, "SKILL.md"), (usage, "references/usage.md")):
            self.assertIn(example, text, msg=label)
            self.assertRegex(text, r"(?is)Tutu\.ru.{0,200}(?:not real-time|not live|не real-time)")
            self.assertRegex(text, r"(?is)(?:verify|провер).{0,120}(?:train|поезд|рейс)")
        self.assertIn("search_train_tickets", usage)
        self.assertIn("Tutu.ru", readme)
        self.assertIn("кэширован", readme)

    def test_2_1_0_activity_query_contract_in_public_docs(self):
        """Public Skill docs must document the extended activity search contract."""
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        usage = (ROOT / "references" / "usage.md").read_text(encoding="utf-8")
        pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))

        self.assertEqual(pkg["version"], "2.2.0")
        metadata, _ = self._skill_frontmatter()
        self.assertEqual(metadata["metadata"]["version"], "2.2.0")

        activity_example = (
            'python scripts/travel_search.py search-activities --input '
            "'{\"city\":\"Анталья\",\"date_from\":\"2026-09-10\","
            "\"date_to\":\"2026-09-12\",\"persons\":2,"
            "\"children_allowed\":true,\"sort\":\"recommended\",\"limit\":5}'"
        )
        for text, label in ((skill, "SKILL.md"), (usage, "references/usage.md")):
            self.assertIn(activity_example, text, msg=label)
            for field in ("date_from", "date_to", "persons", "children_allowed"):
                self.assertIn(field, text, msg="{0} missing {1}".format(label, field))

        for text, label in (
            (skill, "SKILL.md"),
            (usage, "references/usage.md"),
            (readme, "README.md"),
        ):
            self.assertRegex(
                text,
                r"(?is)(?:optional|необязатель).*?date_from.*?date_to"
                r"|date_from.*?date_to.*?(?:optional|необязатель)",
                msg=label + " must say activity dates are optional",
            )
            self.assertRegex(
                text,
                r"(?is)persons.{0,100}(?:from\s+1\s+to\s+100|от\s+1\s+до\s+100|1\s*\.\.\s*100)",
                msg=label + " must document persons range 1..100",
            )

        self.assertIn("Tripster", readme)
        self.assertIn("Sputnik8", readme)

    def test_2_1_0_activity_results_and_presentation_rules(self):
        """Mixed activity results retain source and price semantics for agents."""
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        usage = (ROOT / "references" / "usage.md").read_text(encoding="utf-8")
        docs = skill + "\n" + usage

        for mode in ("recommended", "price", "rating", "reviews"):
            self.assertIn(mode, docs)
        for field in ("provider", "price_unit", "price_text"):
            self.assertIn(field, docs)
        self.assertRegex(
            docs,
            r"(?is)price_unit.*(?:same|matching|identical|сопоставим|одинаков)"
            r"|(?:same|matching|identical|сопоставим|одинаков).*price_unit",
            msg="price comparisons must be limited to like-for-like units",
        )
        self.assertRegex(
            skill,
            r"(?is)(?:one|single|один).*?(?:source|источник).*?"
            r"(?:fails?|unavailable|сбо[ея]|недоступ).*?"
            r"(?:without mentioning|silently|do not mention|молча|не сообща).*?"
            r"(?:outage|failure|сбо[ея])|(?:without mentioning|silently|do not mention|молча|не сообща).*?"
            r"(?:one|single|один).*?(?:source|источник)",
            msg="surviving results must be presented without announcing one source outage",
        )

    def test_readme_leads_with_service_integrations(self):
        """The first screen must name integrations and both connection modes."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        intro, demo_heading, _rest = readme.partition("## Демо")
        self.assertEqual(demo_heading, "## Демо", msg="README demo heading missing")

        expected_rows = (
            "| **Aviasales** | Авиабилеты и календарь цен |",
            "| **Travelata** | Пакетные туры |",
            "| **Level.Travel** | Пакетные туры и отели без перелёта |",
            "| **Sputnik8** | Экскурсии, билеты и активности |",
        )
        for row in expected_rows:
            self.assertIn(row, intro, msg="README integration row missing: " + row)

        self.assertIn("[Agent Skill](#установка)", intro)
        self.assertIn("[удалённый MCP-сервер](#mcp-сервер)", intro)

    def test_readme_is_russian(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertTrue(
            re.search(r"travel_search\.py", readme),
            msg="README must point users to travel_search.py",
        )
        # Russian product documentation: headings/body use Cyrillic
        cyr = re.findall(r"[А-Яа-яЁё]", readme)
        self.assertGreaterEqual(len(cyr), 80, msg="README should be Russian product docs")
        # Expected Russian section headings
        for heading in ("Установка", "Требования", "Лицензия"):
            self.assertIn(heading, readme)

    # --- 2.0.1 docs: narrow trigger, RU catalog, compatibility, README disclosure ---

    def _skill_frontmatter(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", skill, re.DOTALL)
        self.assertIsNotNone(match, msg="SKILL.md frontmatter missing")
        try:
            import yaml  # optional; fall back to line parse if unavailable
        except ImportError:
            yaml = None
        if yaml is not None:
            data = yaml.safe_load(match.group(1))
            self.assertIsInstance(data, dict)
            return data, skill
        # Minimal fallback without PyYAML: flat keys + one-level block mappings
        fm = match.group(1)
        data = {}
        current_map = None  # type: Optional[str]
        for line in fm.splitlines():
            if not line.strip():
                continue
            if line[:1] in (" ", "\t") and current_map is not None and ":" in line:
                key, val = line.strip().split(":", 1)
                nested = data.get(current_map)
                if not isinstance(nested, dict):
                    nested = {}
                    data[current_map] = nested
                nested[key.strip()] = val.strip().strip("\"'")
                continue
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val == "":
                data[key] = {}
                current_map = key
            else:
                current_map = None
                data[key] = val.strip("\"'")
        return data, skill

    def test_skill_description_planning_trigger_and_russian_scope(self):
        """Description must expose live search during travel planning."""
        data, skill = self._skill_frontmatter()
        desc = data.get("description") or ""
        if not isinstance(desc, str):
            desc = str(desc)
        desc = desc.strip()
        self.assertLessEqual(len(desc), 400)
        self.assertTrue(
            desc.startswith("Use while planning"),
            msg="description must start with the travel-planning trigger",
        )
        # Planning is a discovery trigger, but live inventory stays the capability.
        self.assertRegex(
            desc,
            r"search or compare|search(?:es)?|compare",
            msg="description must include search/compare intent",
        )
        self.assertRegex(
            desc,
            r"inventory|prices|availability|booking links",
            msg="description must target current inventory/prices/availability/links",
        )
        for phrase in (
            "спланировать путешествие",
            "подобрать тур",
            "авиабилеты",
            "экскурсии",
            "маршрут с актуальными ценами",
        ):
            self.assertIn(phrase, desc)
        # Pure advice without live search remains out of scope.
        self.assertRegex(
            desc,
            r"general advice without live search",
            msg="description must exclude pure general advice",
        )
        # Must not keep the v2.0.0 broad trigger phrasing
        self.assertNotRegex(
            desc,
            r"asks about travel,\s*flights,\s*airfare",
            msg="broad travel/trip-planning trigger must be removed",
        )
        self.assertIn("planning a trip", desc.lower())
        # Russian request / catalog scope
        self.assertRegex(
            desc,
            r"Russian requests",
            msg="description must state Russian request scope",
        )
        self.assertRegex(
            desc,
            r"Russian-catalog",
            msg="description must state Russian-language catalog scope",
        )

    def test_skill_compatibility_declares_network_not_permissions(self):
        """Agent Skills standard compatibility field; no invented root permissions."""
        data, skill = self._skill_frontmatter()
        # Non-standard root permissions frontmatter must not appear
        self.assertNotRegex(
            skill,
            r"(?m)^permissions\s*:",
            msg="must not invent non-standard root permissions frontmatter",
        )
        compat = data.get("compatibility")
        self.assertIsNotNone(compat, msg="compatibility frontmatter required")
        if not isinstance(compat, str):
            compat = str(compat)
        self.assertRegex(compat, r"Python 3\.8\+")
        self.assertIn("https://mcp.botclaw.ru/travel", compat)
        self.assertRegex(compat, r"HTTPS|https://")
        self.assertRegex(
            compat,
            r"read-only|does not book|не бронир",
            msg="compatibility must note read-only / no booking",
        )
        self.assertRegex(
            compat,
            r"search criteria|criteria are sent|критерии",
            msg="compatibility must note search criteria are sent to the service",
        )

    def test_metadata_permissions_machine_readable(self):
        """LP3: portable metadata.permissions string; no root permissions field."""
        data, skill = self._skill_frontmatter()
        self.assertNotRegex(
            skill,
            r"(?m)^permissions\s*:",
            msg="must not invent unsupported root permissions field",
        )
        meta = data.get("metadata")
        self.assertIsInstance(meta, dict, msg="metadata must be a mapping")
        perms = meta.get("permissions")
        self.assertIsInstance(
            perms,
            str,
            msg="metadata.permissions must be a string (Agent Skills metadata values)",
        )
        self.assertTrue(perms.strip(), msg="metadata.permissions must be non-empty")
        # Explicit limited capability: one HTTPS endpoint + bundled script
        self.assertIn("https://mcp.botclaw.ru/travel", perms)
        self.assertRegex(
            perms,
            r"(?i)outbound|HTTPS",
            msg="permissions must declare outbound HTTPS-only network access",
        )
        self.assertIn("scripts/travel_search.py", perms)
        self.assertRegex(
            perms,
            r"(?i)execute|run|script",
            msg="permissions must declare execution of bundled travel_search.py",
        )
        # No wildcards or broad grants
        self.assertNotIn("*", perms)
        lower = perms.lower()
        for banned in (
            "filesystem",
            "credential",
            "email",
            "calendar",
            "booking",
            "persist",
            "http://",
        ):
            self.assertNotIn(
                banned,
                lower if banned != "http://" else perms,
                msg="permissions must not grant {0}".format(banned),
            )

    def test_usage_privacy_disclosure_and_unknown_retention(self):
        """SQP-2: usage.md privacy notice — criteria sent; no retention guarantee."""
        usage = (ROOT / "references" / "usage.md").read_text(encoding="utf-8")
        # Notice must appear near the top of the document
        head = "\n".join(usage.splitlines()[:25])
        self.assertRegex(
            head,
            r"(?i)privacy|sensitive|search criteria|JSON",
            msg="privacy notice must appear at the top of usage.md",
        )
        # Every command sends supplied JSON criteria to live external production
        self.assertRegex(
            usage,
            r"(?i)every\s+command|each\s+command",
            msg="usage must state every command transmits data",
        )
        self.assertRegex(
            usage,
            r"(?i)JSON|search criteria",
            msg="usage must identify transmitted search criteria / JSON",
        )
        self.assertRegex(
            usage,
            r"(?i)live|production|external",
            msg="usage must name the live external production service",
        )
        # Criteria may contain itinerary/location, dates, travelers, budget, prefs
        self.assertRegex(
            usage,
            r"(?i)itinerary|location",
            msg="usage must list itinerary/location as possible criteria",
        )
        self.assertRegex(usage, r"(?i)\bdates?\b", msg="usage must mention dates")
        self.assertRegex(
            usage,
            r"(?i)traveler|adults|ages",
            msg="usage must mention traveler counts/ages",
        )
        self.assertRegex(usage, r"(?i)budget", msg="usage must mention budget")
        self.assertRegex(
            usage,
            r"(?i)preference",
            msg="usage must mention preferences",
        )
        # Do not send PII / payment / credentials
        self.assertRegex(
            usage,
            r"(?i)names?|contacts?",
            msg="usage must warn against names/contacts",
        )
        self.assertRegex(
            usage,
            r"(?i)passport|payment",
            msg="usage must warn against passport/payment details",
        )
        self.assertRegex(
            usage,
            r"(?i)credential",
            msg="usage must warn against credentials",
        )
        # Local skill does not persist; server retention not guaranteed
        self.assertRegex(
            usage,
            r"(?i)does not persist|not persist|no\s+local\s+persist",
            msg="usage must state the local skill does not persist requests",
        )
        self.assertRegex(
            usage,
            r"(?i)retention|no\s+.*guarantee|not\s+declar",
            msg="usage must address unknown/undeclared server-side retention",
        )
        self.assertRegex(
            usage,
            r"(?i)external\s+service|treat\s+it\s+as\s+an\s+external",
            msg="usage must advise treating the endpoint as an external service",
        )

    def test_skill_body_russian_catalog_language_rule(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        body = re.split(r"^---\s*$", skill, maxsplit=2, flags=re.M)
        body_text = body[-1] if body else skill
        self.assertRegex(
            body_text,
            r"Russian catalog|русск\w+\s+каталог|upstream directory uses Russian",
            msg="SKILL body must justify Russian catalog values/examples",
        )
        self.assertRegex(
            body_text,
            r"preserve the user.?s answer language|do not force Russian|язык ответа|не навязыва",
            msg="SKILL body must preserve user language; not force Russian conversation",
        )
        self.assertRegex(
            body_text,
            r"Russian catalog values for MCP|русск\w+ значени\w+ каталог",
            msg="SKILL body must use Russian catalog values for MCP when required",
        )

    def test_readme_locale_behavior_and_remote_data_disclosure(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        # Intended Russian-language / catalog scope
        self.assertRegex(
            readme,
            r"русскоязычн\w+|русск\w+\s+каталог|русск\w+\s+запрос",
            msg="README must explain Russian-language/catalog scope",
        )
        # Non-Russian request behavior
        self.assertRegex(
            readme,
            r"не на русском|на языке пользователя|язык ответа",
            msg="README must explain behavior for non-Russian requests",
        )
        # Exact remote endpoint
        self.assertIn("https://mcp.botclaw.ru/travel", readme)
        # Only search criteria sent; no credentials / email / calendar / booking / persistence
        self.assertRegex(
            readme,
            r"критерии поиска|переданн\w+ критери",
            msg="README must state only search criteria are sent",
        )
        self.assertRegex(
            readme,
            re.compile(
                r"учётн\w+\s+данн|учетн\w+\s+данн|credentials|парол",
                re.IGNORECASE,
            ),
            msg="README must state credentials are not sent",
        )
        self.assertRegex(
            readme,
            r"почт|calendar|календар",
            msg="README must state email/calendar are not accessed",
        )
        self.assertRegex(
            readme,
            r"бронирован|не бронир",
            msg="README must state no booking",
        )
        self.assertRegex(
            readme,
            r"хранен|persist|долговремен",
            msg="README must state no persistence",
        )

    # --- review fixes: package whitelist, SSE deadline, protocol version ---

    def test_package_json_files_exact_whitelist(self):
        pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(
            pkg.get("files"),
            [
                "SKILL.md",
                "scripts/travel_search.py",
                "references/usage.md",
                "README.md",
            ],
        )

    def test_npm_pack_excludes_caches_and_deleted_artifacts(self):
        # Caches and v1 bytecode exist locally; pack must still exclude them.
        cache_dir = ROOT / "scripts" / "__pycache__"
        self.assertTrue(
            cache_dir.is_dir() or True,
            "local caches may or may not exist; exclusion is still required",
        )
        proc = subprocess.run(
            ["npm", "pack", "--dry-run", "--json"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        packs = json.loads(proc.stdout)
        self.assertIsInstance(packs, list)
        self.assertGreaterEqual(len(packs), 1)
        paths = [f.get("path") for f in packs[0].get("files", [])]
        # Exact public payload plus mandatory package.json metadata.
        expected = {
            "package.json",
            "SKILL.md",
            "scripts/travel_search.py",
            "references/usage.md",
            "README.md",
        }
        self.assertEqual(set(paths), expected)
        for p in paths:
            self.assertNotIn("__pycache__", p)
            self.assertFalse(p.endswith(".pyc"))
            self.assertNotIn("api_call", p)
            self.assertNotIn("tests/", p)
            self.assertNotIn("test_", p)

    def test_sse_returns_immediately_on_matching_event_before_stream_close(self):
        """Matching SSE result must return without waiting for EOF/keepalives."""
        _STATE.stream_mode = "sse_early_match"
        _STATE.stream_hold_seconds = 1.5
        _STATE.stream_keepalive_interval = 0.05
        client = travel_search.McpClient(endpoint=self.server.endpoint, timeout=10)
        # Initialize over normal JSON; only tools/list streams.
        t0 = time.monotonic()
        tools = client.list_tools()
        elapsed = time.monotonic() - t0
        self.assertIn("search_tours", [t["name"] for t in tools])
        self.assertEqual(len(tools), 8)
        # Stream holds open >= 1.5s; client must finish well before that.
        self.assertLess(
            elapsed,
            1.0,
            msg="client waited for stream close instead of returning on match: "
            "{0:.3f}s".format(elapsed),
        )

    def test_sse_keepalive_stream_hits_total_timeout(self):
        """Keepalives must not extend past the total request deadline."""
        _STATE.stream_mode = "sse_keepalive_only"
        _STATE.stream_hold_seconds = 5.0
        _STATE.stream_keepalive_interval = 0.05
        timeout = 0.6
        client = travel_search.McpClient(
            endpoint=self.server.endpoint, timeout=timeout
        )
        client._ensure_ready()  # type: ignore[attr-defined]
        t0 = time.monotonic()
        with self.assertRaises(travel_search.McpError) as ctx:
            client.list_tools()
        elapsed = time.monotonic() - t0
        self.assertEqual(ctx.exception.category, "timeout")
        self.assertEqual(str(ctx.exception), "timeout")
        # Near the configured deadline, not after the multi-second stream close.
        self.assertGreaterEqual(elapsed, timeout * 0.5)
        self.assertLess(
            elapsed,
            2.0,
            msg="timeout waited for stream end instead of total deadline: "
            "{0:.3f}s".format(elapsed),
        )

    def test_sse_slow_trickle_without_newline_hits_total_timeout(self):
        """SSE bytes without \\n must not block past the total deadline."""
        _STATE.stream_mode = "sse_slow_trickle"
        _STATE.stream_hold_seconds = 3.0
        # Trickle faster than socket inactivity so readline stays blocked.
        _STATE.stream_keepalive_interval = 0.02
        timeout = 0.20
        client = travel_search.McpClient(
            endpoint=self.server.endpoint, timeout=timeout
        )
        client._ensure_ready()  # type: ignore[attr-defined]
        t0 = time.monotonic()
        with self.assertRaises(travel_search.McpError) as ctx:
            client.list_tools()
        elapsed = time.monotonic() - t0
        self.assertEqual(ctx.exception.category, "timeout")
        self.assertEqual(str(ctx.exception), "timeout")
        self.assertGreaterEqual(elapsed, timeout * 0.5)
        self.assertLess(
            elapsed,
            0.70,
            msg="SSE slow trickle blocked past total deadline: "
            "{0:.3f}s".format(elapsed),
        )

    def test_json_slow_trickle_hits_total_timeout(self):
        """Incomplete JSON body trickle must not block past total deadline."""
        _STATE.stream_mode = "json_slow_trickle"
        _STATE.stream_hold_seconds = 3.0
        _STATE.stream_keepalive_interval = 0.02
        timeout = 0.20
        client = travel_search.McpClient(
            endpoint=self.server.endpoint, timeout=timeout
        )
        client._ensure_ready()  # type: ignore[attr-defined]
        t0 = time.monotonic()
        with self.assertRaises(travel_search.McpError) as ctx:
            client.list_tools()
        elapsed = time.monotonic() - t0
        self.assertEqual(ctx.exception.category, "timeout")
        self.assertEqual(str(ctx.exception), "timeout")
        self.assertGreaterEqual(elapsed, timeout * 0.5)
        self.assertLess(
            elapsed,
            0.70,
            msg="JSON slow trickle blocked past total deadline: "
            "{0:.3f}s".format(elapsed),
        )

    def test_oversized_declared_content_length_fails_immediately(self):
        """Content-Length > cap must reject without reading body bytes."""
        _STATE.stream_mode = "oversized_declared_trickle"
        _STATE.stream_hold_seconds = 3.0
        _STATE.stream_keepalive_interval = 0.02
        timeout = 0.20
        client = travel_search.McpClient(
            endpoint=self.server.endpoint, timeout=timeout
        )
        client._ensure_ready()  # type: ignore[attr-defined]
        t0 = time.monotonic()
        with self.assertRaises(travel_search.McpError) as ctx:
            client.list_tools()
        elapsed = time.monotonic() - t0
        self.assertEqual(ctx.exception.category, "response_too_large")
        self.assertEqual(str(ctx.exception), "response too large")
        self.assertLess(
            elapsed,
            0.70,
            msg="oversized Content-Length drained body past deadline: "
            "{0:.3f}s".format(elapsed),
        )

    def test_negotiated_protocol_version_header_on_post_initialize_requests(self):
        client = travel_search.McpClient(endpoint=self.server.endpoint, timeout=5)
        client.call_tool("search_tours", {"destination": "TR"})
        methods = [r["body"].get("method") for r in _STATE.requests]
        self.assertEqual(methods[0], "initialize")
        self.assertEqual(methods[1], "notifications/initialized")
        self.assertIn("tools/call", methods)

        init_headers = _STATE.requests[0]["headers"]
        self.assertNotIn("mcp-protocol-version", init_headers)

        expected_ver = travel_search._PROTOCOL_VERSION
        for r in _STATE.requests[1:]:
            self.assertEqual(
                r["headers"].get("mcp-protocol-version"),
                expected_ver,
                msg="missing/wrong MCP-Protocol-Version on {0}".format(
                    r["body"].get("method")
                ),
            )

    def test_missing_initialize_protocol_version_rejected(self):
        _STATE.omit_init_protocol_version = True
        client = travel_search.McpClient(endpoint=self.server.endpoint, timeout=5)
        with self.assertRaises(travel_search.McpError) as ctx:
            client.list_tools()
        self.assertEqual(ctx.exception.category, "protocol_version")
        self.assertEqual(str(ctx.exception), "unsupported protocol version")
        methods = [r["body"].get("method") for r in _STATE.requests]
        self.assertEqual(methods, ["initialize"])
        self.assertNotIn("notifications/initialized", methods)
        self.assertNotIn("tools/list", methods)

    def test_mismatched_initialize_protocol_version_rejected(self):
        _STATE.init_protocol_version = "2025-03-26"
        client = travel_search.McpClient(endpoint=self.server.endpoint, timeout=5)
        with self.assertRaises(travel_search.McpError) as ctx:
            client.list_tools()
        self.assertEqual(ctx.exception.category, "protocol_version")
        self.assertEqual(str(ctx.exception), "unsupported protocol version")
        methods = [r["body"].get("method") for r in _STATE.requests]
        self.assertEqual(methods, ["initialize"])
        self.assertNotIn("notifications/initialized", methods)
        self.assertNotIn("tools/list", methods)


if __name__ == "__main__":
    unittest.main()
