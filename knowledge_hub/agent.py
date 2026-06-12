from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types as genai_types

from .config import USE_LOCAL_RAG
from .settings_store import get_agent_settings
from .tools.add_data import add_data
from .tools.create_corpus import create_corpus
from .tools.delete_corpus import delete_corpus
from .tools.delete_document import delete_document
from .tools.get_corpus_info import get_corpus_info
from .tools.rag_query import rag_query

_agent_settings = get_agent_settings()

root_agent = Agent(
    name="RagAgent",
    model=_agent_settings["model"],
    description="Peak Rock Engineering Intelligence Oracle — governance SOPs and production code",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=False)
    ),
    tools=[
        rag_query,
        get_corpus_info,
        create_corpus,
        add_data,
        delete_corpus,
        delete_document,
    ],
    instruction=_agent_settings["instruction"],
)
