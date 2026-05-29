from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types as genai_types

from .config import USE_LOCAL_RAG
from .oracle_instruction import ORACLE_INSTRUCTION
from .tools.add_data import add_data
from .tools.create_corpus import create_corpus
from .tools.delete_corpus import delete_corpus
from .tools.delete_document import delete_document
from .tools.get_corpus_info import get_corpus_info
from .tools.list_corpora import list_corpora
from .tools.rag_query import rag_query

root_agent = Agent(
    name="RagAgent",
    model="gemini-2.5-flash",
    description="Aegis Manufacturing Oracle — SOPs, rules, and production code",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=False)
    ),
    tools=[
        rag_query,
        list_corpora,
        create_corpus,
        add_data,
        get_corpus_info,
        delete_corpus,
        delete_document,
    ],
    instruction=ORACLE_INSTRUCTION,
)
