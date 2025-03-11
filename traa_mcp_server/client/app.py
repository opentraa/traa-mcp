"""TRAA MCP client implementation"""

import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env
            
class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.tools = []

    async def refresh_tools(self):
        """Refresh the list of available tools"""
        response = await self.session.list_tools()
        self.tools = response.tools
    
    async def print_tools(self):
        """Print available tools"""

        # list tools and their descriptions and parameters
        for tool in self.tools:
            print(f"\nTool: {tool.name}")
            print(f"Description: {tool.description}")
            
            if tool.inputSchema.get('properties'):
                required_params = tool.inputSchema.get('required', [])
                print("Parameters:")
                for param in required_params:
                    param_info = tool.inputSchema['properties'].get(param, {})
                    param_type = param_info.get('type', 'unknown')
                    print(f"  - {param} ({param_type})")
                    if 'description' in param_info:
                        print(f"    Description: {param_info['description']}")

    async def connect_to_server(self):
        """Connect to an MCP server"""
        server_params = StdioServerParameters(
            command="traa_mcp_server",  # Use the installed script
            args=[],  # No additional args needed
            env=None,  # Optional environment variables
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        print("\nConnected to server")
        
        await self.refresh_tools()
        await self.print_tools()

    async def chat_loop(self):
        """Run an interactive chat loop"""

        print("\nMCP Client Started!")
        
        while True:
            try:
                print("\nSelect a tool to use or 'quit' to exit.")
                await self.print_tools()
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break

                # if query is not a tool name, just continue
                if query not in [tool.name for tool in self.tools]:
                    print("\n*********Invalid tool name. Please try again.*********")
                    continue
                
                # Find the selected tool
                selected_tool = next(tool for tool in self.tools if tool.name == query)
                
                # Collect parameters if the tool has any
                params = {}
                if selected_tool.inputSchema.get('properties'):
                    required_params = selected_tool.inputSchema.get('required', [])
                    print(f"\nPlease enter the required parameters for {selected_tool.name}:")
                    
                    for param in required_params:
                        param_info = selected_tool.inputSchema['properties'].get(param, {})
                        param_type = param_info.get('type', 'unknown')
                        description = param_info.get('description', '')
                        
                        print(f"\n{param} ({param_type})")
                        if description:
                            print(f"Description: {description}")
                            
                        value = input("Enter value: ").strip()
                        
                        # Convert value based on parameter type
                        if param_type == 'integer':
                            value = int(value)
                        elif param_type == 'number':
                            value = float(value)
                        elif param_type == 'array':
                            # Assuming array input is comma-separated values
                            value = [int(x.strip()) for x in value.split(',')]
                        elif param_type == 'boolean':
                            value = value.lower() in ('true', 'yes', '1', 't')
                            
                        params[param] = value
                
                # Call the tool with collected parameters
                print(f"\nCalling tool: {selected_tool.name} with params: {params}")

                # TODO @sylar: the call will not return, need to be resolved
                response = await self.session.call_tool(selected_tool.name, params)
                print("\nTool Response:")
                print(response.content)
                    
            except ValueError as e:
                print(f"\nError: Invalid input - {str(e)}")
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def _main_impl():
    client = MCPClient()
    try:
        await client.connect_to_server()
        await client.chat_loop()
    finally:
        await client.cleanup()

# to support run in command with uv run traa_mcp_client
def main():
    import sys
    asyncio.run(_main_impl())

if __name__ == "__main__":
    main()
