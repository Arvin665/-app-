"""Pixso MCP 本地客户端。

桌面会话未直接暴露画布工具时，本脚本通过标准 Streamable HTTP MCP
连接本机 Pixso 服务，仅用于读取工具、调用设计工具并输出 JSON 结果。
"""

import argparse
import base64
import asyncio
import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

PIXSO_MCP_URL = "http://localhost:3667/mcp"


async def connect_and_run(command: str, tool_name: str | None, arguments: dict[str, Any]) -> Any:
    async with streamable_http_client(PIXSO_MCP_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            if command == "list":
                result = await session.list_tools()
                return [
                    tool.model_dump(mode="json", by_alias=True)
                    for tool in result.tools
                ]
            result = await session.call_tool(tool_name or "", arguments=arguments)
            payload: dict[str, Any] = {
                "isError": bool(result.is_error),
                "content": [],
                "structuredContent": getattr(result, "structured_content", None),
            }
            for item in result.content:
                text = getattr(item, "text", None)
                payload["content"].append(text if text is not None else item.model_dump(mode="json"))
            return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", choices=["list", "call"], default="list")
    parser.add_argument("--tool")
    parser.add_argument("--args", default="{}")
    parser.add_argument("--args-base64")
    options = parser.parse_args()
    if options.args_base64:
        raw_args = base64.b64decode(options.args_base64).decode("utf-8")
    else:
        raw_args = options.args
    arguments = json.loads(raw_args)
    result = asyncio.run(connect_and_run(options.command, options.tool, arguments))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
