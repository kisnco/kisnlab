"""LangGraph dev agent: ReAct loop with GitHub PR review tools.

State is the Pydantic ``DevState`` from ``app.agents.state``. The system
prompt is composed from markdown skill fragments via ``load_skills``.
"""

from __future__ import annotations

import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent

from app.agents.observability import LANGFUSE_CALLBACKS
from app.agents.skills import load_skills
from app.agents.state import DevState
from app.agents.tools.github_tools import GITHUB_PR_TOOLS

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"
DEV_SKILLS = ("dev_base", "github_pr_tools")


def _build_system_prompt() -> str:
    return load_skills(DEV_SKILLS)


_SYSTEM_PROMPT: str = _build_system_prompt()


def call_claude(state: DevState) -> dict:
    """Run the ReAct loop over the conversation history.

    ``state.messages`` carries prior turns when the team supervisor delegates a
    multi-turn thread. For a one-shot ``/agents/dev/run`` the list is empty, so
    we fall back to a single ``HumanMessage`` built from ``state.task``.
    """
    history = list(state.messages) if state.messages else [HumanMessage(content=state.task)]
    llm = ChatAnthropic(model=MODEL, max_tokens=4096)
    react_agent = create_react_agent(llm, tools=GITHUB_PR_TOOLS)
    result = react_agent.invoke(
        {"messages": [SystemMessage(content=_SYSTEM_PROMPT), *history]},
        config={"callbacks": LANGFUSE_CALLBACKS, "run_name": "dev_agent"},
    )
    final_message = result["messages"][-1]
    content = final_message.content
    if isinstance(content, list):
        # Claude tool-calling can return content as a list of blocks; keep text only.
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return {"response": content}


def build_dev_graph():
    graph = StateGraph(DevState)
    graph.add_node("call_claude", call_claude)
    graph.add_edge(START, "call_claude")
    graph.add_edge("call_claude", END)
    return graph.compile()
