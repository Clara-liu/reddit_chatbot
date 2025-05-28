import os
import asyncio
import nest_asyncio

from google import genai
from dotenv import load_dotenv
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters, types
from typing import List

nest_asyncio.apply()

load_dotenv()


class RedditChatbot:
    def __init__(self):
        self.session: ClientSession = None
        self.googleai = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
        self.available_tools: List[dict] = []
    
    async def process_query(self, query: str):
        relevant_subs = await self.session.call_tool(
            name="search_for_subreddits",
            arguments={"query":query}
        )
        print("The subreddits related to your query are:\n", "\n".join(relevant_subs.content[0].text.split("+")))
        
        response = await self.googleai.aio.models.generate_content(
            model='gemini-2.0-flash',
            contents=query,
        )
        # TODO: add logic to use tools and prompt llm
        # TODO: add prompt server
        print(f"\nGemini's response:\n{response.text}")


    async def chat_loop(self):
        print("\n Reddit Chatbot Starting!")
        print("Type your question or 'quit' to exit!")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == "quit":
                    break
                    
                await self.process_query(query)
                print("\n")
            except Exception as e:
                print(f"Error encountered: {str(e)}")


    async def connect_to_server_and_run(self):
        # Create server parameters for stdio connection
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "reddit_server.py"],
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                await session.initialize()  # handshake with server

                res = await session.list_tools()
                print(f"\nConnected to reddit server with tools:{[tool.name for tool in res.tools]}")

                self.available_tools = [{
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                } for tool in res.tools]

                await self.chat_loop()

async def main():
    chatbot = RedditChatbot()
    await chatbot.connect_to_server_and_run()


if __name__ == "__main__":
    asyncio.run(main())
