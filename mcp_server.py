import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pypdf import PdfReader
import sys

app = Server("pdf-reader-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="extract_text",
            description="Extract text content from a PDF file given its absolute path.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The absolute path to the PDF file on the local filesystem."
                    }
                },
                "required": ["file_path"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != "extract_text":
        raise ValueError(f"Unknown tool: {name}")
    
    file_path = arguments.get("file_path")
    if not file_path:
        raise ValueError("file_path is required")

    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        return [TextContent(type="text", text=text)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error reading PDF: {str(e)}")]

async def main():
    # Run the MCP server using standard I/O
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
