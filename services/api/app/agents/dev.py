"""LangGraph dev agent: ReAct loop with GitHub PR review tools.

Public API ``build_dev_graph()`` keeps the ``{"task", "response"}`` shape so
the router/tests stay untouched. Inside, we delegate to ``create_react_agent``
which handles the tool-calling loop.
"""

from __future__ import annotations

from typing import TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent

from app.agents.tools.github_tools import GITHUB_PR_TOOLS

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = (
    "Tu es l'agent dev de KisnLab, le bras technique de KIS'n Code. "
    "Tu reponds en francais. Le code que tu produis est en anglais. "
    "Tu vises la solution la plus simple qui fonctionne (philosophie KIS). "
    "Tu es concis : pas de blabla, droit au but.\n\n"
    "Outils GitHub disponibles :\n"
    "- gh_pr_list(repo, state) : lister les PRs.\n"
    "- gh_pr_get(repo, number) : metadata d'une PR.\n"
    "- gh_pr_diff(repo, number) : diff unifie.\n"
    "- gh_pr_review(repo, number, event, body) : APPROVE / REQUEST_CHANGES / COMMENT.\n"
    "- gh_pr_comment(repo, number, body) : simple commentaire.\n"
    "Pour reviewer : lis d'abord le diff (gh_pr_diff), puis poste une review "
    "structuree. Approuve seulement si tu n'as pas de remarque bloquante."
)


class DevState(TypedDict):
    task: str
    response: str


def call_claude(state: DevState) -> DevState:
    llm = ChatAnthropic(model=MODEL, max_tokens=4096)
    react_agent = create_react_agent(llm, tools=GITHUB_PR_TOOLS)
    result = react_agent.invoke(
        {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                ("user", state["task"]),
            ]
        }
    )
    final_message = result["messages"][-1]
    content = final_message.content
    if isinstance(content, list):
        # Claude tool-calling can return content as a list of blocks; keep text only.
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return {"task": state["task"], "response": content}


def build_dev_graph():
    graph = StateGraph(DevState)
    graph.add_node("call_claude", call_claude)
    graph.add_edge(START, "call_claude")
    graph.add_edge("call_claude", END)
    return graph.compile()
