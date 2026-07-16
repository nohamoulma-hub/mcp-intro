# mcp-intro

## MCP Architecture Summary

**MCP (Model Context Protocol)** is an open protocol that standardizes how AI applications connect to external data sources and tools. Instead of every application building custom, one-off integrations, MCP defines a common interface so any compliant client can talk to any compliant server.

**An MCP host** is the user-facing AI application (e.g. an IDE, a chat app, an agent runtime) that manages the overall interaction with the user and coordinates one or more MCP clients to reach external servers.

**An MCP client** lives inside the host and maintains a 1:1 connection with a single MCP server. It handles the protocol-level communication (requests, responses, notifications) between the host and that server.

**An MCP server** exposes specific capabilities tools, resources, and prompts — to clients over the protocol. A server typically wraps an external system (a database, an API, a filesystem, etc.) and translates it into the standardized MCP interface.

**Tools** are functions the server exposes that the model can invoke to perform actions or computations (e.g. running a query, calling an API, writing a file). They have defined inputs/outputs and side effects the model can trigger.

**Resources** are data the server exposes for the client to read (e.g. file contents, database records, documents). Unlike tools, resources are meant to provide context rather than perform actions.

**The key difference between tools and resources** is that tools are active and resources are passive. A tool does something it can have side effects (write a file, call an API, modify data) and typically requires input parameters to run. A resource simply provides something to read it feeds context to the model without triggering any action or change in the outside world. In short: tools let the model *act*, resources let the model *know*.

**A server should expose only the capabilities it really needs** because every exposed tool and resource is a piece of attack surface and a source of potential misuse: it can be invoked by a model that may misinterpret intent, chained in unexpected ways, or exploited if the connection is compromised. Minimizing exposed capabilities reduces the blast radius of mistakes or malicious use, keeps permissions easy to reason about, and follows the principle of least privilege.

### My take on what an MCP server is

An MCP server is like a specialized tool supplier that provides a specific toolbox (e.g. plumbing tools, or electrical tools). Without it, the worker has to do everything by hand or improvise. With it, the worker gets access to dedicated tools that make their work faster, more reliable, and expand what they're capable of doing but only within the domain that this supplier covers.