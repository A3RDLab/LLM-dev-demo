# thought_server.py
from mcp.server.fastmcp import FastMCP

# 1. Initialize the FastMCP server with a descriptive name
mcp = FastMCP("AgentThoughtLogger")

# 2. Define the tool using the @mcp.tool() decorator
@mcp.tool()
def thinking(thought: str) -> str:
  """
  Write an intermediate thought or reasoning step of the ReAct agent 
  before it reaches the final answer.
  
  Args:
      thought: The string containing the agent's current thought or reasoning step.
  
  Returns:
      Confirmation of the thought.
  """
  # Server-side action: You can simply print the thought for logging/debugging
  # or store it somewhere if needed.
  # print(f"[Agent Thought Recorded]: {thought}")
  
  # Return the required "OK" confirmation to the agent
  return "OK"

# 3. Add the standard boilerplate to run the server if executed directly
if __name__ == "__main__":
  # Run the server using stdio transport by default
  # This is suitable for local testing and integration with clients like Claude Desktop
  mcp.run(transport='stdio') 
  # print("Agent Thought Logger MCP Server running on stdio...") 
  # Note: The print statement above might not be visible when run via Claude Desktop, 
  # as stdout is used for MCP communication. Use stderr for server logs if needed,
  # or use the logging capabilities of MCP itself (ctx.info, ctx.error etc. inside tools).
