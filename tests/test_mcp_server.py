"""Tests for Model Context Protocol (MCP) JSON-RPC 2.0 server over stdio."""

import json
import pytest

from og_canvas_forge.mcp_server import (
    PROTOCOL_VERSION,
    SERVER_NAME,
    SERVER_VERSION,
    handle_jsonrpc_request,
)


def test_mcp_initialize_handshake():
    """Verify MCP initialize handshake returns server info and protocol version."""
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"},
        },
    }
    resp = handle_jsonrpc_request(req)
    assert resp is not None
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    assert "result" in resp
    assert resp["result"]["serverInfo"]["name"] == SERVER_NAME
    assert resp["result"]["serverInfo"]["version"] == SERVER_VERSION
    assert "tools" in resp["result"]["capabilities"]


def test_mcp_ping():
    """Verify JSON-RPC ping request."""
    req = {"jsonrpc": "2.0", "id": "test-ping-1", "method": "ping"}
    resp = handle_jsonrpc_request(req)
    assert resp is not None
    assert resp["id"] == "test-ping-1"
    assert resp["result"] == {}


def test_mcp_tools_list():
    """Verify MCP tools list returns available tools with schemas."""
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    resp = handle_jsonrpc_request(req)
    assert resp is not None
    assert "result" in resp
    tools = resp["result"]["tools"]
    assert isinstance(tools, list)
    assert len(tools) >= 4

    tool_names = [t["name"] for t in tools]
    assert any("generate" in name or "card" in name for name in tool_names)


def test_mcp_tools_call_generate():
    """Verify calling card generation tool via MCP JSON-RPC."""
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "og_generate_card",
            "arguments": {
                "title": "MCP Generated OpenGraph Card",
                "subtitle": "Testing tool execution over JSON-RPC stdio",
                "theme": "aurora",
                "category": "Testing",
                "tags": ["MCP", "Testing"],
            },
        },
    }
    resp = handle_jsonrpc_request(req)
    assert resp is not None
    assert resp["id"] == 3
    assert "result" in resp
    content = resp["result"].get("content", [])
    assert len(content) > 0
    # Check for SVG content
    svg_text = content[0].get("text", "")
    assert "<svg" in svg_text
    assert "MCP Generated OpenGraph Card" in svg_text


def test_mcp_resources_and_prompts():
    """Verify MCP resources and prompts list endpoints."""
    # Resources
    req_res = {"jsonrpc": "2.0", "id": 4, "method": "resources/list"}
    resp_res = handle_jsonrpc_request(req_res)
    assert "resources" in resp_res["result"]

    # Prompts
    req_prompt = {"jsonrpc": "2.0", "id": 5, "method": "prompts/list"}
    resp_prompt = handle_jsonrpc_request(req_prompt)
    assert "prompts" in resp_prompt["result"]


def test_mcp_invalid_request_handling():
    """Verify error responses for malformed JSON and unknown methods."""
    # Parse error (invalid string)
    resp1 = handle_jsonrpc_request("{ invalid json")
    assert resp1["error"]["code"] == -32700

    # Method not found
    req2 = {"jsonrpc": "2.0", "id": 99, "method": "non_existent_method"}
    resp2 = handle_jsonrpc_request(req2)
    assert resp2["error"]["code"] == -32601
