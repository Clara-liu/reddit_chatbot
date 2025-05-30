import os
import asyncio
import nest_asyncio

from google import genai
from dotenv import load_dotenv
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters, types
from utils import process_narrow_subs_response

nest_asyncio.apply()

load_dotenv()


class RedditChatbot:
    def __init__(self):
        self.session: ClientSession = None
        self.googleai = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
        self.verbose = False
    
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

        # Extracts text from prompt content (handles different formats)        
        process_prompt = lambda x: x if isinstance(x, str) else x.text

        prompt = process_prompt(subreddit_prompt)

        narrowed_subs = await self.process_sub_reddit_narrowing(prompt)
        relevant_posts = await self.session.call_tool(
            name="search_reddit",
            arguments={"query": query, "subreddits": narrowed_subs, "top_k": 15}
        )
        relevant_posts = relevant_posts.content[0].text
        # TODO: add method to process post narrowing with titles and finally process summarys
        

    async def process_sub_reddit_narrowing(self, prompt: str)-> str:
        response = await self.googleai.aio.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        # get + delimited subreddit names
        processed_response = process_narrow_subs_response(response.text)
        if self.verbose:
            print(f"\nGemini's response:\n{response.text}")
        else:
            print(f"Input to search reddit for relevant posts: {processed_response}")
        return processed_response


    async def chat_loop(self):
        print("\n Reddit Chatbot Starting!")
        print("Type your question or 'quit' to exit!")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == "quit":
                    break
                verbosity = input("\nWould you like to see LLM thinking process? Type 'Yes' or skip" \
                "for no.").lower()
                if verbosity == "yes":
                    self.verbose = True
                elif verbosity == "" or verbosity == "no":
                    self.verbose = False
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
