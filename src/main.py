#!/usr/bin/env python3
"""
Basic MCP Server for managing dotfiles.
"""

import asyncio
import json
import os
import subprocess
import sys
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

app = Server("dotfiles-server")


def run_git_command(*args) -> subprocess.CompletedProcess:
    """Run a git command with the bare repository configuration."""
    git_dir = os.path.expanduser("~/.cfg")
    work_tree = os.path.expanduser("~")

    cmd = ["git", f"--git-dir={git_dir}", f"--work-tree={work_tree}", *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def list_dotfiles() -> List[str]:
    """List all files managed by the dotfiles repository."""
    result = run_git_command("ls-files")
    if result.returncode != 0:
        return []
    return [f.strip() for f in result.stdout.split("\n") if f.strip()]


def get_file_content(filepath: str) -> str:
    """Get the content of a specific dotfile."""
    full_path = os.path.join(os.path.expanduser("~"), filepath)
    if not os.path.exists(full_path):
        return f"File not found: {filepath}"

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


@app.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="list_dotfiles",
            description="List all dotfiles managed by the repository",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_dotfile_content",
            description="Get the content of a specific dotfile",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the dotfile"}
                },
                "required": ["filepath"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    if name == "list_dotfiles":
        files = list_dotfiles()
        if not files:
            text = "No dotfiles found or git repository not accessible."
        else:
            text = f"Found {len(files)} dotfiles:\n\n" + "\n".join(files)

        return [TextContent(type="text", text=text)]

    elif name == "get_dotfile_content":
        filepath = arguments.get("filepath", "")
        if not filepath:
            return [TextContent(type="text", text="Error: filepath is required")]

        content = get_file_content(filepath)
        return [TextContent(type="text", text=f"Content of {filepath}:\n\n{content}")]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        # Try different initialization approaches
        try:
            # Method 1: With full initialization options
            init_options = InitializationOptions(
                server_name="dotfiles-server",
                server_version="1.0.0",
                capabilities=app.get_capabilities(None, None),
            )
            await app.run(read_stream, write_stream, init_options)
        except Exception as e1:
            try:
                # Method 2: With empty capabilities
                init_options = InitializationOptions(
                    server_name="dotfiles-server",
                    server_version="1.0.0",
                    capabilities={},
                )
                await app.run(read_stream, write_stream, init_options)
            except Exception as e2:
                # Method 3: Minimal approach
                await app.run(read_stream, write_stream, InitializationOptions())


if __name__ == "__main__":
    asyncio.run(main())
