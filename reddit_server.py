import praw
import os

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv


load_dotenv()


mcp = FastMCP("reddit")


@mcp.tool()
def search_reddit(query: str, top_k: int = 10) -> list:
    """
    search reddit for relevant content

    Args:
        query (str): user query
        top_k (int, optional): how many results to return. Defaults to 10.

    Returns:
        list: e.g. [
        {"url": "https://example.com", "title": "my title"}, ...]
    """
    get_var = lambda x: os.environ.get(x)
    reddit = praw.Reddit(
        client_id = get_var("REDDIT_CLIENT_ID"),
        client_secret = get_var("REDDIT_CLIENT_SECRET"),
        user_agent = get_var("REDDIT_AGENT"),
        password = get_var("REDDIT_PASSWORD"),
        username = get_var("REDDIT_USERNAME")
    )
    results = []
    for submission in reddit.subreddit("all").search(query):
        results.append({"url": submission.url, "title": submission.title})
        if len(results) == top_k:
            return results


if __name__ == "__main__":
    mcp.run(transport="stdio")