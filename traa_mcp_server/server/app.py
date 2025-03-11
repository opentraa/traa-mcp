"""TRAA MCP server implementation"""

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.types import Image
import logging
import sys
import asyncio
import click

from traa_mcp_server.tools.snapshot import (
    enum_screen_sources, 
    create_snapshot,
    save_snapshot,
    SimpleScreenSourceInfo
)

# Configure logging to write to stderr
logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("traa_mcp_server.mcp")


def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server instance"""
    server = FastMCP(
        "TRAA MCP Server",
        host="localhost",
        port=3001,
        dependencies=["traa"],
    )

    # Register all tools with the server
    register_tools(server)

    return server


def register_tools(mcp_server: FastMCP) -> None:
    """Register all MCP tools with the server"""

    @mcp_server.tool(
        name="enum_screen_sources",
        description="Enumerate all screen and window sources available on the system and return a list of SimpleScreenSourceInfo",
    )
    def enum_screen_sources_tool() -> list[SimpleScreenSourceInfo]:
        """Wrapper around the enum_screen_sources tool implementation"""
        return enum_screen_sources()
    
    @mcp_server.tool(
        name="create_snapshot",
        description="Create a snapshot of the screen source with the given ID and return it as an image",
    )
    def create_snapshot_tool(source_id: int, snapshot_size: tuple[int, int]) -> Image:
        """Wrapper around the create_snapshot tool implementation"""
        return create_snapshot(source_id, snapshot_size)

    @mcp_server.tool(
        name="save_snapshot",
        description="Save a snapshot of the screen source with the given ID to a file",
    )
    def save_snapshot_tool(source_id: int, snapshot_size: tuple[int, int], file_path: str) -> None:
        """Wrapper around the save_snapshot tool implementation"""
        return save_snapshot(source_id, snapshot_size, file_path)


# Create a server instance that can be imported by the MCP CLI
server = create_mcp_server()


@click.command()
@click.option("--port", default=3001, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type (stdio or sse)",
)
def main(port: int, transport: str) -> int:
    """Run the server with specified transport."""
    try:
        if transport == "stdio":
            asyncio.run(server.run_stdio_async())
        else:
            server.settings.port = port
            asyncio.run(server.run_sse_async())
        return 0
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
