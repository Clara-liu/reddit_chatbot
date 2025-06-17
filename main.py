import os
import json
import asyncio
import nest_asyncio

from google import genai
from dotenv import load_dotenv
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters, types
from utils import process_scope_narrow_response, process_prompt

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
        subreddit_prompt = process_prompt(subreddit_prompt)

        narrowed_subs = await self.process_sub_reddit_narrowing(subreddit_prompt)
        relevant_posts = await self.session.call_tool(
            name="search_reddit",
            arguments={"query": query, "subreddits": narrowed_subs, "top_k": 15}
        )
        relevant_posts = [json.loads(x.text) for x in relevant_posts.content]
        relevant_posts_titles = "+".join([x["title"] for x in relevant_posts])

        post_prompt = await self.session.get_prompt(
            name="generate_narrow_posts_prompt",
            arguments={"reddit_results": relevant_posts_titles, "query": query}
        )
        post_prompt = process_prompt(post_prompt)
        # "post1+post2" or "none"
        narrowed_posts: str = await self.process_post_reddit_narrowing(post_prompt)
        narrowed_posts = narrowed_posts.split("+")
        if 'none' in narrowed_posts and len(narrowed_posts)==1:
            print("I'm sorry, but we couldn't find any relevant context on reddit." \
            "Here is the LLM's vanilla response.")
            response = await self.googleai.aio.models.generate_content(
                model='gemini-2.0-flash',
                contents=query,
            )
            print(response.text)
        else:
            filter_func = lambda x: x["title"] in narrowed_posts
            relevant_posts = filter(filter_func, relevant_posts)
            relevant_posts_with_body = [
                await self.session.call_tool(
                    name="get_submission_info",
                    arguments={"submission_info": x, "k_top_comment": 10}
                )
                for x in relevant_posts
            ]
            summary_prompt = await self.session.get_prompt(
                name="generate_summary_prompt",
                arguments={"reddit_results": str(relevant_posts_with_body), "query": query}
            )
            summary_prompt = process_prompt(summary_prompt)
            answer = await self.googleai.aio.models.generate_content(
                model='gemini-2.0-flash',
                contents=summary_prompt)
            print(answer.text)
        

    async def process_post_reddit_narrowing(self, prompt: str)-> str:
        response = await self.googleai.aio.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        # get + delimited subreddit names
        processed_response = process_scope_narrow_response(response.text)
        if self.verbose:
            print(f"\nGemini's response:\n{response.text}")
        else:
            print(f"Input to LLM for post summary: {processed_response}")
        return processed_response


    async def process_sub_reddit_narrowing(self, prompt: str)-> str:
        response = await self.googleai.aio.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        # get + delimited subreddit names
        processed_response = process_scope_narrow_response(response.text)
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
