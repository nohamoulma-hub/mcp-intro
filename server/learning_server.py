#!/usr/bin/env python3
""" Script for fastmcp """


import json
from pathlib import Path

from fastmcp import FastMCP

mcp = FastMCP("Programming Learning Server")

# Path to the local topic dataset (relative to this file, not the cwd)
TOPICS_PATH = Path(__file__).parent.parent / "data" / "topics.json"


def _load_topics() -> list[dict]:
    """Read and parse the topic dataset. Shared by all tools/resources below."""
    with open(TOPICS_PATH, encoding="utf-8") as f:
        return json.load(f)


@mcp.tool
def search_topics(query: str) -> list[dict]:
    """Search programming topics by title or keyword."""
    query = query.strip().lower()
    topics = _load_topics()

    # Keep only topics matching the query in their title or one of their key concepts.
    # Return a short summary per match, not the full topic (agent picks one, then
    # calls get_topic_details for the rest).
    return [
        {"id": topic["id"], "title": topic["title"], "summary": topic["summary"]}
        for topic in topics
        if query in topic["title"].lower()
        or any(query in concept.lower() for concept in topic["key_concepts"])
    ]


@mcp.tool
def get_topic_details(topic_id: str) -> dict:
    """Return full information for a topic by id."""
    topics = _load_topics()

    # Exact match on id (not a partial/fuzzy search like search_topics).
    for topic in topics:
        if topic["id"] == topic_id:
            return topic

    # No exception on invalid input: return a clear error payload instead.
    return {"error": f"No topic found with id '{topic_id}'"}


# Read-only resource: exposes data, not an action. Accessed by URI instead of being called.
@mcp.resource("topics://catalog")
def get_topic_catalog() -> str:
    """Return the list of available topic ids and titles."""
    topics = _load_topics()

    # Lightweight catalog for browsing (id + title only, no full details).
    catalog = [{"id": topic["id"], "title": topic["title"]} for topic in topics]

    # Resources must return text, so the list is serialized to a JSON string.
    return json.dumps(catalog)


if __name__ == "__main__":
    # HTTP transport so the client can connect over http://localhost:8000/mcp
    mcp.run(transport="http", host="localhost", port=8000, path="/mcp")
