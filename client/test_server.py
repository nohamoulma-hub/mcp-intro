import asyncio
from fastmcp import Client

client = Client("http://localhost:8000/mcp")


async def main():
    async with client:
        print("=== Server starts / connects ===")
        print("OK (connected)")

        print("\n=== Tools are listed ===")
        tools = await client.list_tools()
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")

        print("\n=== search_topics with a valid query ===")
        result = await client.call_tool("search_topics", {"query": "decorator"})
        print(result.data)

        print("\n=== get_topic_details with a valid topic id ===")
        result = await client.call_tool("get_topic_details", {"topic_id": "python-decorators"})
        print(result.data)

        print("\n=== Catalog resource can be read ===")
        resource = await client.read_resource("topics://catalog")
        print(resource[0].text)

        print("\n=== Invalid inputs return understandable errors ===")
        result = await client.call_tool("get_topic_details", {"topic_id": "does-not-exist"})
        print("get_topic_details('does-not-exist') ->", result.data)

        result = await client.call_tool("search_topics", {"query": "zzz-nothing-matches"})
        print("search_topics('zzz-nothing-matches') ->", result.data)


asyncio.run(main())
