# MCP Servers in Python

## Description

This project is a small **Programming Learning MCP Server**: a local dataset of programming topics ([`data/topics.json`](data/topics.json)) exposed over the Model Context Protocol. It includes:

- an MCP server ([`server/learning_server.py`](server/learning_server.py)) exposing search/detail tools and a catalog resource,
- test clients ([`client/mcp_client.py`](client/mcp_client.py), [`client/test_server.py`](client/test_server.py)) to call it directly,
- an LLM-based agent ([`client/agent.py`](client/agent.py)) that answers a student's question by calling the MCP server for topic information.

## MCP Architecture Summary

**MCP (Model Context Protocol)** is an open protocol that standardizes how AI applications connect to external data sources and tools. Instead of every application building custom, one-off integrations, MCP defines a common interface so any compliant client can talk to any compliant server.

**An MCP host** is the user-facing AI application (e.g. an IDE, a chat app, an agent runtime) that manages the overall interaction with the user and coordinates one or more MCP clients to reach external servers.

**An MCP client** lives inside the host and maintains a 1:1 connection with a single MCP server. It handles the protocol-level communication (requests, responses, notifications) between the host and that server.

**An MCP server** exposes specific capabilities (tools, resources, and prompts) to clients over the protocol. A server typically wraps an external system (a database, an API, a filesystem, etc.) and translates it into the standardized MCP interface.

**Tools** are functions the server exposes that the model can invoke to perform actions or computations (e.g. running a query, calling an API, writing a file). They have defined inputs/outputs and side effects the model can trigger.

**Resources** are data the server exposes for the client to read (e.g. file contents, database records, documents). Unlike tools, resources are meant to provide context rather than perform actions.

**The key difference between tools and resources** is that tools are active and resources are passive. A tool does something, it can have side effects (write a file, call an API, modify data) and typically requires input parameters to run. A resource simply provides something to read, it feeds context to the model without triggering any action or change in the outside world. In short: tools let the model *act*, resources let the model *know*.

**A server should expose only the capabilities it really needs** because every exposed tool and resource is a piece of attack surface and a source of potential misuse: it can be invoked by a model that may misinterpret intent, chained in unexpected ways, or exploited if the connection is compromised. Minimizing exposed capabilities reduces the blast radius of mistakes or malicious use, keeps permissions easy to reason about, and follows the principle of least privilege.

My take on what an MCP server is: it's like a specialized tool supplier that provides a specific toolbox (e.g. plumbing tools, or electrical tools). Without it, the worker has to do everything by hand or improvise. With it, the worker gets access to dedicated tools that make their work faster, more reliable, and expand what they're capable of doing, but only within the domain that this supplier covers.

## Requirements

- Python 3.10+
- [`fastmcp`](https://pypi.org/project/fastmcp/)
- [`ollama`](https://pypi.org/project/ollama/) Python client (only needed for the agent)
- [Ollama](https://ollama.com) installed and running locally (only needed for the agent), with the `llama3.2:1b` model pulled

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Or with `uv`:

```bash
uv add fastmcp ollama
```

If you plan to run the agent, also install and start Ollama, then pull the model:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull llama3.2:1b
```

## How to Run the Server

```bash
source venv/bin/activate
python3 server/learning_server.py
```

The server listens on `http://localhost:8000/mcp` (HTTP transport). Leave it running in its own terminal.

## How to Test the Server

With the server running, in another terminal:

```bash
source venv/bin/activate
python3 client/test_server.py
```

[`client/test_server.py`](client/test_server.py) connects over HTTP and verifies:

- **The server starts**: the client connects successfully to `http://localhost:8000/mcp`.
- **The tools are listed**: `client.list_tools()` returns `search_topics` and `get_topic_details`.
- **`search_topics` works**: a valid query (e.g. `"decorator"`) returns matching topic summaries.
- **`get_topic_details` works**: a valid topic id (e.g. `"python-decorators"`) returns the full topic object.
- **The catalog resource can be read**: `client.read_resource("topics://catalog")` returns the JSON list of ids/titles.
- **Invalid inputs return understandable errors**: an unknown topic id returns `{"error": "..."}` instead of crashing, and a query with no matches returns `[]` instead of an exception.

## How to Run the Agent

With the MCP server running and Ollama running with `llama3.2:1b` pulled:

```bash
source venv/bin/activate
python3 -u client/agent.py
```

The question asked is the `STUDENT_QUESTION` string at the top of `agent.py`. Edit it there to try a different question. Generation takes ~50-100s on CPU-only hardware. The answer is printed to the terminal and saved to `output/sample_agent_response.md`.

`agent.py` uses no agent framework (e.g. Google ADK). The connection to MCP is handled directly with the [`fastmcp`](https://pypi.org/project/fastmcp/) Python client:

- `fastmcp.Client("http://localhost:8000/mcp")` opens an HTTP connection to the running MCP server (same client used in `mcp_client.py` and `test_server.py`).
- `search_topics` and `get_topic_details` are described to the LLM as Ollama tool schemas (`TOOLS` in `agent.py`), so the model can request them by name.
- When the model requests a tool call, `call_mcp_tool()` forwards it to the MCP server via `mcp_client.call_tool(name, arguments)`, the actual MCP tool call rather than a local Python function call.
- The MCP server's response is fed back into the conversation so the model can use it to write the final answer.
- Run with `python3 -u client/agent.py` to see `[AGENT]`/`[MCP]` trace logs confirming each MCP call as it happens.

## Available Tools

- **`search_topics(query: str) -> list[dict]`**: searches topics by title or key concept (case-insensitive substring match). Returns a list of `{id, title, summary}`, or `[]` if nothing matches.
- **`get_topic_details(topic_id: str) -> dict`**: returns the full topic object (`id`, `title`, `summary`, `prerequisites`, `key_concepts`, `common_mistakes`, `practice_idea`) for an exact topic id, or `{"error": "..."}` if the id doesn't exist.

## Available Resources

- **`topics://catalog`**: read-only resource returning a compact JSON list of all available `{id, title}` pairs in the topic dataset, for browsing without fetching full details.

## Third-Party MCP Server Review

Reviewed the official [`mcp-server-fetch`](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch) server (part of the reference servers maintained by the Model Context Protocol project). Inspected via its README and configuration examples, not installed or run.

- **What it does**: retrieves a web page and converts its HTML content to markdown for the model to read.
- **Local or remote**: runs **locally** as a subprocess over stdio, started with `uvx mcp-server-fetch`, `pip`, or a Docker image (`mcp/fetch`). It is not a hosted/remote service: the host application launches it as a child process.
- **Tools/resources exposed**: a single tool, `fetch(url, max_length, start_index, raw)`, plus a matching `fetch` prompt. No resources.
- **Permissions/credentials required**: none. No API key or login needed to run it. However, once running it can make **outbound HTTP requests to any URL it's given**, including local/internal network addresses. The project's own README explicitly warns about this.
- **One risk**: because the `fetch` tool accepts an arbitrary URL, a prompt-injected instruction (e.g. hidden text on a fetched page) could make the agent fetch an internal address (e.g. a cloud metadata endpoint like `169.254.169.254` or an internal admin panel) and leak its response back into the conversation, a server-side request forgery (SSRF) style risk.
- **One safety measure**: run the server with network egress restricted to public internet only (e.g. a container/firewall rule blocking RFC 1918 private ranges and the `169.254.169.254` link-local metadata address), so even a malicious `fetch` call can't reach internal services.

## Example Output

Sample run for the question *"I want to study Python decorators. What should I review first?"*, saved in [`output/sample_agent_response.md`](output/sample_agent_response.md):

```
To study Python decorators effectively, it would be helpful to review the basics of functions and scope first. Decorators are a fundamental concept in Python programming, allowing you to modify or extend the behavior of existing functions without changing their source code.

One practice idea that you can explore is creating a decorator that logs function calls, including their arguments and execution time. This can help you understand the inner workings of decorators and how they interact with other functions in your code.

[...full answer in output/sample_agent_response.md...]
```

## Known Limitations

**Small local model reliability.** `llama3.2:1b` was chosen because it is lightweight enough to run on this machine (no GPU, 7.7 GB RAM). At this size, tool-calling is not fully reliable:

- The model does not always chain `search_topics` → `get_topic_details` on its own. `agent.py` compensates by explicitly nudging the model to call `get_topic_details` right after a `search_topics` match, before it is allowed to answer.
- Even with matching data returned by the MCP server, the model sometimes phrases its answer inconsistently (e.g. claiming "no topic found" while still listing that topic's real key concepts and practice idea). This is a text-generation quality issue in the model, not an MCP integration issue: the correct data was retrieved and used, just described awkwardly.

Given the hardware constraints, a larger model (tested: `llama3.2:3b`) caused heavy swapping and was not usable here. If running on a machine with more RAM or a GPU, a bigger or better-tool-calling model (e.g. `llama3.2:3b`, `qwen2.5:3b`) would likely produce more consistent phrasing.

**Errors encountered during development:**

- `address already in use` on port 8000: happened whenever a previous `learning_server.py` process was left running. Fixed by finding and killing the stale process before starting a new one.
- Malformed tool-call arguments from the small model: `llama3.2:1b` sometimes echoed the whole tool schema back as arguments (e.g. `{"parameters": {"query": "..."}}`) instead of just `{"query": "..."}`, causing an MCP `ToolError`. Fixed with a `clean_arguments()` step in `agent.py` that unwraps this case before calling the MCP server.
- `qwen2.5:1.5b` was tested as an alternative model but performed worse: it answered from pretrained knowledge without calling any MCP tool at all in some runs. Reverted to `llama3.2:1b`.

## Reflection

**What problem does MCP solve?**
It standardizes how AI applications connect external tools and data sources. Instead of every app building custom one-off integrations, MCP defines a common protocol so any compliant client can talk to any compliant server, making tools reusable across different AI applications.

**What is the difference between an MCP tool and an MCP resource?**
A tool is active: it performs an action or computation and can have side effects (e.g. `search_topics` searches, `get_topic_details` looks up data). A resource is passive: it exposes data for reading, with no action triggered (e.g. `topics://catalog`, which just returns the topic list). Tools let the model *act*, resources let the model *know*.

**What does your MCP server expose?**
Two tools (`search_topics`, `get_topic_details`) and one resource (`topics://catalog`), all backed by a local JSON dataset of programming topics ([`data/topics.json`](data/topics.json)).

**How does your agent use the MCP server?**
It connects with `fastmcp.Client` over HTTP, describes `search_topics` and `get_topic_details` to an Ollama LLM as callable tools, and lets the model decide when to call them. Tool calls are forwarded to the real MCP server (not local Python functions), and the returned data is fed back into the conversation for the model to use in its final answer.

**What should you check before using a third-party MCP server?**
What it actually does, whether it runs locally or remotely, exactly which tools/resources it exposes, what credentials or permissions it requires, and what it can reach or access once running (e.g. network, filesystem). As shown in the Fetch server review above, even a server with no required credentials can still carry real risk (e.g. SSRF) through the capabilities it exposes.

**What limitation did you observe in your implementation?**
The MCP server integration itself is solid and well-tested (verified with `test_server.py` and trace logs in `agent.py`), but the small local LLM (`llama3.2:1b`, chosen for the 7.7 GB RAM, no-GPU environment) doesn't reliably chain tool calls or phrase its final answer consistently, even when it has correctly retrieved the right data. This is a model-quality limitation, not an MCP protocol or server limitation.
