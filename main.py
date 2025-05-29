import os
import asyncio
import nest_asyncio

from google import genai
from dotenv import load_dotenv
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters, types

nest_asyncio.apply()

load_dotenv()


class RedditChatbot:
    def __init__(self):
        self.session: ClientSession = None
        self.googleai = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    
    async def process_query(self, query: str):
        relevant_subs = await self.session.call_tool(
            name="search_for_subreddits",
            arguments={"query": query, "top_k": 40}
        )
        relevant_subs = relevant_subs.content[0].text
        print("Using tool search_for_subreddits.\nThe subreddits related to your query are:\n",
            "\n".join(relevant_subs.split("+"))
        )
        subreddit_prompt = await self.session.get_prompt(
            name="generate_narrow_subs_prompt",
            arguments={"reddit_results": relevant_subs, "query": query}
        )
        subreddit_prompt = subreddit_prompt.messages[0].content
        
        # Extract text from content (handles different formats)
        if isinstance(subreddit_prompt, str):
            prompt = subreddit_prompt
        elif hasattr(subreddit_prompt, 'text'):
            prompt = subreddit_prompt.text

        response = await self.googleai.aio.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        # TODO: add logic to use tools and prompt llm
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
                tools = await session.list_tools()
                print(f"\nConnected to reddit server with tools:{[tool.name for tool in tools.tools]}")

                prompts = await session.list_prompts()
                print(f"\nConnected to reddit server with prompts:{[prompt.name for prompt in prompts.prompts]}")

                await self.chat_loop()

async def main():
    chatbot = RedditChatbot()
    await chatbot.connect_to_server_and_run()


if __name__ == "__main__":
    asyncio.run(main())
