import asyncio
import json

import ollama
from fastmcp import Client

mcp_client = Client("http://localhost:8000/mcp")

MODEL = "llama3.2:1b"

# Sample student question used to generate output/sample_agent_response.md.
# Change this string to try a different question.
STUDENT_QUESTION = "I want to study Python decorators. What should I review first?"

SYSTEM_PROMPT = (
    "You are a programming study assistant.\n\n"
    "When the user asks about a topic, first call search_topics to find a "
    "matching topic. If it returns a match, you must then call get_topic_details "
    "with its id before writing any answer.\n\n"
    "Use only the returned MCP data to answer. Include prerequisites, key "
    "concepts, common mistakes, and one practice idea when available.\n\n"
    "Do not invent topic details that were not provided by the MCP server. "
    "If no topic matches, explain that clearly.\n\n"
    "Give a concise, student-facing answer."
)

# Tool schemas describing our MCP tools to the LLM, so it can decide when to call them.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_topics",
            "description": "Search programming topics by title or keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword to search for"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_topic_details",
            "description": "Return full information for a topic by id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic_id": {"type": "string", "description": "Exact id of the topic"},
                },
                "required": ["topic_id"],
            },
        },
    },
]


async def call_mcp_tool(name: str, arguments: dict) -> str:
    """Forward a tool call chosen by the LLM to the actual MCP server."""
    print(f"[MCP] calling {name}({arguments}) on the MCP server...")
    async with mcp_client:
        result = await mcp_client.call_tool(name, arguments)
        print(f"[MCP] {name} returned: {result.data}")
        return json.dumps(result.data)


def clean_arguments(arguments: dict) -> dict:
    """Small models sometimes echo the whole tool schema back instead of just
    the parameters (e.g. {"parameters": {"query": "..."}}). Unwrap that case."""
    if "parameters" in arguments and isinstance(arguments["parameters"], dict):
        return arguments["parameters"]
    return arguments


MAX_ROUNDS = 4  # safety net in case a small model keeps asking for tool calls


async def run_agent(question: str) -> str:
    """Let the LLM decide when to call the MCP tools, then return its final answer."""
    print(f"[AGENT] received student request: {question!r}")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    called_get_details = False

    for _ in range(MAX_ROUNDS):
        response = ollama.chat(model=MODEL, messages=messages, tools=TOOLS)
        message = response["message"]
        messages.append(message)

        tool_calls = message.get("tool_calls")
        if not tool_calls:
            print("[AGENT] final answer ready (no more tool calls requested)")
            return message["content"]

        for call in tool_calls:
            tool_name = call["function"]["name"]
            tool_args = clean_arguments(call["function"]["arguments"])
            tool_result = await call_mcp_tool(tool_name, tool_args)
            messages.append({"role": "tool", "content": tool_result, "name": tool_name})

            if tool_name == "get_topic_details":
                called_get_details = True

            # Small models tend to answer right after search_topics without
            # following up, ignoring the returned summary. Nudge them to
            # fetch full details before writing the final answer.
            if tool_name == "search_topics" and not called_get_details:
                matches = json.loads(tool_result)
                if matches:
                    topic_id = matches[0]["id"]
                    messages.append({
                        "role": "user",
                        "content": (
                            f"Now call get_topic_details with topic_id='{topic_id}' "
                            "before answering."
                        ),
                    })

    # Ran out of rounds without a final answer: ask the model to wrap up using
    # whatever tool results are already in the conversation.
    messages.append({"role": "user", "content": "Please give your final answer now."})
    response = ollama.chat(model=MODEL, messages=messages)
    return response["message"]["content"]


async def main():
    answer = await run_agent(STUDENT_QUESTION)

    print(answer)

    with open("output/sample_agent_response.md", "w", encoding="utf-8") as f:
        f.write(answer)


asyncio.run(main())
