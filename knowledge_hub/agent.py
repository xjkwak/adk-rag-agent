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


def _build_adk_model(provider: str, model: str):
    """Return the ADK-compatible model value for the given provider.

    For Gemini, returns the plain model-ID string.
    For OpenAI, wraps the model in a LiteLlm object so the ADK routes
    requests through LiteLLM → OpenAI.
    """
    if provider == "openai":
        from google.adk.models.lite_llm import LiteLlm  # type: ignore[import]

        return LiteLlm(model=f"openai/{model}")
    return model


_agent_settings = get_agent_settings()
_initial_provider = _agent_settings.get("provider", "gemini")
_initial_model    = _build_adk_model(_initial_provider, _agent_settings["model"])
_initial_planner  = (
    BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=False)
    )
    if _initial_provider == "gemini"
    else None
)

root_agent = Agent(
    name="RagAgent",
    model=_initial_model,
    description=(
        "Peak Rock Engineering Intelligence Oracle — technical due "
        "diligence over governance SOPs and production code"
    ),
    planner=_initial_planner,
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
