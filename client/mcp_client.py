import asyncio
from fastmcp import Client

client = Client("http://localhost:8000/mcp")

async def main():
    async with client:
        result = await client.call_tool("search_topics", {"query": "decorators"})
        print(result)

asyncio.run(main())
