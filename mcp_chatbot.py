from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List
import asyncio
import nest_asyncio

nest_asyncio.apply()

load_dotenv()

class MCP_ChatBot:

    def __init__(self):
        # Initialize the MCP client session and client objects
        self.session: ClientSession = None
        self.anthropic = Anthropic()
        self.available_tools: List[dict] = []


    async def proess_query(self, query):

        messages= [{'role': 'user', 'content': query}]

        response = self.anthropic.messages.create(max_tokens =2024,
                                          model = 'claude-sonnet-4-6',
                                      tools = self.available_tools,
                                      messages = messages
                                      )

        process_query = True

        while process_query:
            assistant_content = []

            for content in response.content:
                if content.type == 'text':
                    print(content.text)
                    assistant_content.append(content)
                    if len(response.content) == 1:
                        process_query = False

                elif content.type == 'tool_use':
                    assistant_content.append(content)
                    messages.append({'role': 'assistant', 'content': assistant_content})

                    tool_id = content.id
                    tool_args = content.input
                    tool_name = content.name

                    print(f"Calling tool {tool_name} with arguments: {tool_args}")

                    # tool invokation through the client session
                    result = await self.session.call_tool(tool_name, arguments=tool_args)
                    tool_result_content = [{"type": block.type, "text": block.text} for block in result.content]
                    messages.append({'role': 'user',
                                 "content": [
                                 {
                                        "type": "tool_result",
                                        "tool_use_id": tool_id,
                                        "content": tool_result_content
                                 }
                            ]
                            })
                    response = self.anthropic.messages.create(max_tokens =2024,
                                                    model = 'claude-sonnet-4-6',
                                                    tools = self.available_tools,
                                                    messages = messages)

                    if len(response.content) == 1 and response.content[0].type == 'text':
                        print(response.content[0].text)
                        process_query = False



    async def chat_loop(self):
        """Run a interactive chat loop"""
        print("\nMCP chatbot Started.!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    print("Goodbye!")
                    break

                await self.proess_query(query)

                print ("\n--- End of response ---")
            except Exception as e:
                print(f"An error occurred: {str(e)}")             

    async def connect_to_server_and_run(self):
        # Create server parameters for stdio connection
        server_params = StdioServerParameters(
            command = "uv",  # Executable
            args = ["run", "research_server.py"],  # Arguments to start the server
            env = None,  # Environment variables (optional)
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                # Initialize the connection and fetch available tools
                await self.session.initialize()

                # List available tools
                response = await self.session.list_tools()

                tools = response.tools
                print(f"Connected to Server with tools: ", [tool.name for tool in tools])

                self.available_tools = [{
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                } for tool in response.tools]

                await self.chat_loop()

async def main():
    chatbot = MCP_ChatBot()
    await chatbot.connect_to_server_and_run()


if __name__ == "__main__":
    asyncio.run(main())
