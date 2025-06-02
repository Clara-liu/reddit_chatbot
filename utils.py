import os
import asyncpraw

import mcp.types as types

from contextlib import asynccontextmanager


@asynccontextmanager
async def reddit_context():
    get_var = lambda x: os.environ.get(x)
    try:
        reddit = asyncpraw.Reddit(
            client_id = get_var("REDDIT_CLIENT_ID"),
            client_secret = get_var("REDDIT_CLIENT_SECRET"),
            user_agent = get_var("REDDIT_AGENT"),
            password = get_var("REDDIT_PASSWORD"),
            username = get_var("REDDIT_USERNAME")
        )
        yield reddit
    finally:
        await reddit.close()


def process_scope_narrow_response(raw_response: str) -> str:
    """
    "All men ```must``` die" -> "must"
    """
    return raw_response.split("```")[1]


def process_prompt(prompt: types.GetPromptResult) -> str:
        prompt = prompt.messages[0].content
        # Extracts text from prompt content (handles different formats)
        if isinstance(prompt, str):
             return prompt
        else:
             return prompt.text