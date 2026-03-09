"""
Playwright MCP Client Wrapper.

Provides an async context manager to start the @playwright/mcp server
via stdio transport and exposes browser automation methods:
navigate, snapshot, screenshot, click, type.

Used by the crawler for accessibility-based element discovery.
Falls back gracefully if MCP server is unavailable.
"""

import asyncio
import json
import logging
import shutil
from contextlib import asynccontextmanager

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class MCPBrowserClient:
    """
    Client for the Playwright MCP server using stdio JSON-RPC transport.

    The MCP server is started as a subprocess and communicates via
    stdin/stdout using the JSON-RPC 2.0 protocol.
    """

    def __init__(self, process: asyncio.subprocess.Process):
        self._process = process
        self._request_id = 0

    async def _send_request(self, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC request and read the response."""
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
        }
        if params:
            request["params"] = params

        payload = json.dumps(request)
        # MCP uses content-length header framing over stdio
        message = f"Content-Length: {len(payload)}\r\n\r\n{payload}"

        self._process.stdin.write(message.encode())
        await self._process.stdin.drain()

        # Read response with content-length framing
        response_data = await self._read_response()
        return response_data

    async def _read_response(self) -> dict:
        """Read a JSON-RPC response with content-length framing."""
        # Read headers until we find Content-Length
        content_length = 0
        while True:
            line = await asyncio.wait_for(
                self._process.stdout.readline(), timeout=30.0
            )
            line_str = line.decode().strip()
            if line_str == "":
                break  # End of headers
            if line_str.lower().startswith("content-length:"):
                content_length = int(line_str.split(":")[1].strip())

        if content_length == 0:
            raise RuntimeError("No Content-Length in MCP response")

        # Read the JSON body
        body = await asyncio.wait_for(
            self._process.stdout.readexactly(content_length), timeout=30.0
        )
        return json.loads(body.decode())

    async def initialize(self) -> dict:
        """Send the MCP initialize handshake."""
        result = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "ai-agent-test", "version": "1.0.0"},
        })
        # Send initialized notification
        notification = json.dumps({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })
        message = f"Content-Length: {len(notification)}\r\n\r\n{notification}"
        self._process.stdin.write(message.encode())
        await self._process.stdin.drain()
        return result

    async def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        """Call an MCP tool by name."""
        params = {"name": name}
        if arguments:
            params["arguments"] = arguments
        return await self._send_request("tools/call", params)

    async def navigate(self, url: str) -> dict:
        """Navigate the browser to a URL."""
        return await self.call_tool("browser_navigate", {"url": url})

    async def snapshot(self) -> dict:
        """Get an accessibility snapshot of the current page."""
        return await self.call_tool("browser_snapshot")

    async def screenshot(self) -> dict:
        """Take a screenshot of the current page."""
        return await self.call_tool("browser_screenshot")

    async def click(self, element: str, ref: str) -> dict:
        """Click an element by its ref."""
        return await self.call_tool("browser_click", {
            "element": element,
            "ref": ref,
        })

    async def type_text(self, element: str, ref: str, text: str) -> dict:
        """Type text into an element by its ref."""
        return await self.call_tool("browser_type", {
            "element": element,
            "ref": ref,
            "text": text,
        })

    async def close(self):
        """Terminate the MCP server process."""
        if self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()


def _get_mcp_command() -> list[str]:
    """Parse the MCP command string into a list of arguments."""
    parts = settings.playwright_mcp_command.split()
    # Resolve npx to npx.cmd on Windows
    if parts[0] == "npx":
        npx_path = shutil.which("npx.cmd") or shutil.which("npx")
        if npx_path:
            parts[0] = npx_path
    return parts


def is_mcp_available() -> bool:
    """Check if the MCP command is available on PATH."""
    parts = settings.playwright_mcp_command.split()
    cmd = parts[0]
    if cmd == "npx":
        return bool(shutil.which("npx.cmd") or shutil.which("npx"))
    return bool(shutil.which(cmd))


@asynccontextmanager
async def create_mcp_client():
    """
    Async context manager that starts the Playwright MCP server
    and yields an MCPBrowserClient.

    Usage:
        async with create_mcp_client() as client:
            await client.navigate("https://example.com")
            snapshot = await client.snapshot()
    """
    cmd = _get_mcp_command()
    logger.info("Starting Playwright MCP server: %s", " ".join(cmd))

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    client = MCPBrowserClient(process)
    try:
        await client.initialize()
        logger.info("Playwright MCP server initialized")
        yield client
    finally:
        await client.close()
        logger.info("Playwright MCP server stopped")
