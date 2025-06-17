# Reddit chatbot using MCP
This is a demo project that uses MCP to create a chatbot that uses information on reddit to answer user queries.
## Installation (after cloning this repo)
1. First, install `uv` as the environment manager. A guide can be found [here](https://docs.astral.sh/uv/getting-started/installation/).
2. Install the dependencies by running `uv sync` in the root dir of this repo.
3. Create a dotenv file in the root directory of this project,
include the following:
```
REDDIT_CLIENT_ID="<your client ID>"
REDDIT_CLIENT_SECRET="<your client secret>"
REDDIT_AGENT="<your agent>"
REDDIT_USERNAME="<your user name>"
REDDIT_PASSWORD="<your pw>"
GOOGLE_API_KEY="<your google api key>"
```
The reddit related fields are required to use the python reddit
API as a script app. You can create your own reddit app to obtain these by following this guide: https://praw.readthedocs.io/en/stable/getting_started/quick_start.html.

The google API key is to authenticate to google so we can use the gemini models (I choose this for its free tier benefit).

There should not be any cost if you run this with a google account without a paying plan attached.

4. Once the dotenv file is ready and the environment is setup, run `source .venv/bin/activate`, then `uv run main.py`.