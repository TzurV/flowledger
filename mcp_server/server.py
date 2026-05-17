from mcp.server.fastmcp import FastMCP

from mcp_server.tools import notes, projects, tasks

mcp = FastMCP("flowledger")

projects.register(mcp)
tasks.register(mcp)
notes.register(mcp)


def main() -> None:
    # FastMCP.run() defaults to the stdio transport: it reads JSON-RPC
    # messages from stdin and writes responses to stdout. That is exactly
    # what a coding assistant expects when it launches the server.
    mcp.run()


if __name__ == "__main__":
    main()
