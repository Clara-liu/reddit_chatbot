from itertools import islice
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from utils import reddit_context


load_dotenv()


mcp = FastMCP("reddit")


@mcp.tool()
async def search_reddit(query: str, subreddits: str, top_k: int = 10) -> list | str:
    """
    search reddit for relevant content.

    Args:
        query (str): user query
        subreddits (str): sub names delimited  by "+"
        top_k (int, optional): how many results to return. Defaults to 10.

    Returns:
        list: e.g. [
        {"url": "https://example.com", "title": "my title"}, ...]
        or
        str: error message
    """
    async with reddit_context() as reddit:
        sub = await reddit.subreddit(subreddits)
        results = []
        try:
            async for submission in sub.search(query, limit=None, syntax="cloudsearch"):
                if submission.is_self:
                    results.append({"url": submission.url, "title": submission.title, "id": submission.id})
                if len(results) == top_k:
                    break
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
    async with reddit_context() as reddit:
        results = {
            "url": submission_info["url"],
            "body": None,
            "top_k_comments": None,
            "title": submission_info["title"]
        }
        try:
            submission = await reddit.submission(submission_info["id"])
            results["top_k_comments"] = islice(submission.comments, k_top_comment+1)
            results["top_k_comments"] = [x.body for x in results["top_k_comments"]]
            results["body"] = submission.selftext
            return results
        except Exception as e:
            return f"Error: {e}"


@mcp.tool()
async def search_for_subreddits(query: str, top_k = 25)-> str:
    """
    Search reddit for relevant subreddits to user query.

    Args:
        query (str): user query
        top_k (int, optional): how many subs to return. Defaults to 25.

    Returns:
        str: subreddit display names delimited by "+"
    """
    results = []
    async with reddit_context() as reddit:
        try:
            subs = reddit.subreddits
            async for sub in subs.search(query):
                # filter out NSFW subs
                if not sub.over18:
                    results.append(sub.display_name)
                if len(results) == top_k:
                    break
            return '+'.join(results)
        except Exception as e:
            return f"Error: {e}"


@mcp.prompt()
def generate_narrow_subs_prompt(reddit_results: str, query: str) -> str:
    """
    generates prompt for LLM to narrow down subreddits
    """
    return f""" We want to search reddit for relevant posts to the user's query:
    {query}
    ---
    A subreddit search on reddit yields these subreddits as relevant to the user's query:
    {', '.join(reddit_results.split('+'))}.
    ---
    Can you narrow down the the relevant subreddits by doing the following 4 steps:
    1. First, see if there are any subreddits that are not relevant to the user's query
    2. If there are, remove the irrelevant subreddits and return the subset in the following format:
        subreddit1+subreddit2+subreddit3 (i.e. subreddit names delimited by the + sign)
    3. If there are no irrelevant subreddits, return the original set of subreddits in the format
        mentioned in point 2
    4. If there are no relevant subreddits, return the string 'all'
    Return the + delimited subreddit names by surrounding them in triple backticket like so
    ```sub1+sub2+sub3```
    """


@mcp.prompt()
def generate_narrow_posts_prompt(reddit_results: str, query: str) -> str:
    """
    generates prompt for LLM to narrow down posts. input example:
    'post1+post2+post3'
    """
    return f""" We want to narrow relevant posts on reddit related to the user's query:
    {query}
    ---
    A search on reddit yields these posts as relevant to the user's query:
    {reddit_results}.
    ---
    Can you narrow down the the relevant posts by analysing their titles,
     by doing the following 4 steps:
    1. First, see if there are any posts that are not relevant to the user's query
    2. If there are, remove the irrelevant posts and return the subset in the following format:
        post1+post2+post3
    3. If there are no irrelevant posts, return the original set of posts in the format
        mentioned in point 2
    4. If there are no relevant posts, return the string 'none'
    Return the + delimited posts titles by surrounding them in triple backticket like so
    ```post1+post2+post3```
    """


@mcp.prompt()
def generate_summary_prompt(reddit_results: str, query: str) -> str:
    """
    generates prompt for LLM to summarise finds on reddit to answer user query
    """
    return f""" We want to summarise these posts on reddit and use them
    to answer the user's query:
    {query}.
    The posts follow this format:
    {{
            "url": "https://example.com",
            "body": "I have body hair",
            "top_k_comments":[
                "all",
                "men",
                "must",
                "die"
            ]
            "title": "my title"
        }}
    
    ---
    You are given a list of posts as follows:
    ---
    {reddit_results}
    ---
    Please read through all of them, then give your summary in 
    natural language to answer the user's query.
    Also, give a link to the source when appropriate.
    """


if __name__ == "__main__":
    mcp.run(transport="stdio")