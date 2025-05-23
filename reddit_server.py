import asyncpraw
import os

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv


load_dotenv()


mcp = FastMCP("reddit")

get_var = lambda x: os.environ.get(x)


@mcp.tool()
async def search_reddit(query: str, top_k: int = 10) -> list | str:
    """
    search reddit for relevant content. does not need async as all must be returned for LLM
    to choose top k relevant submissions

    Args:
        query (str): user query
        top_k (int, optional): how many results to return. Defaults to 10.

    Returns:
        list: e.g. [
        {"url": "https://example.com", "title": "my title"}, ...]
        or
        str: error message
    """
    async with asyncpraw.Reddit(
        client_id = get_var("REDDIT_CLIENT_ID"),
        client_secret = get_var("REDDIT_CLIENT_SECRET"),
        user_agent = get_var("REDDIT_AGENT"),
        password = get_var("REDDIT_PASSWORD"),
        username = get_var("REDDIT_USERNAME")
    ) as reddit:
        sub = await reddit.subreddit("all")
        results = []
        try:
            async for submission in sub.search(query):
                results.append({"url": submission.url, "title": submission.title, "id": submission.id})
                if len(results) == top_k:
                    return results
        except Exception as e:
            return f"Error: {e}"


@mcp.tool()
async def get_submission_info(submission_info: dict, k_top_comment: int = 8) -> dict | str:
    """
    get the text body and top n comments 

    Args:
        submission_info (dict): the dict containing url, id and title of a submission,
        as returned by `search_reddit()`

    Returns:
        dict: e.g.{
            "url": "https://example.com",
            "body": "I have body hair",
            "top_k_comments":[
                "all",
                "men",
                "must",
                "die"
            ]
            "title": "my title"
        }
        or
        str: error message
    """
    async with asyncpraw.Reddit(
        client_id = get_var("REDDIT_CLIENT_ID"),
        client_secret = get_var("REDDIT_CLIENT_SECRET"),
        user_agent = get_var("REDDIT_AGENT"),
        password = get_var("REDDIT_PASSWORD"),
        username = get_var("REDDIT_USERNAME")
    ) as reddit:
        results = {
            "url": submission_info["url"],
            "body": None,
            "top_k_comments": None,
            "title": submission_info["title"]
        }
        try:
            submission = await reddit.submission(submission_info["id"])
            results["top_k_comments"] = [submission.comments[i].body for i in range(k_top_comment)]
            results["body"] = submission.selftext
            return results
        except Exception as e:
            return f"Error: {e}"





if __name__ == "__main__":
    mcp.run(transport="stdio")