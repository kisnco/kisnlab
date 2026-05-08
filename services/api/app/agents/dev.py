from typing import TypedDict

from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, START, StateGraph

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = (
    "Tu es l'agent dev de KisnLab, le bras technique de KIS'n Code. "
    "Tu réponds en français, le code que tu produis est en anglais. "
    "Tu vises la solution la plus simple qui fonctionne (philosophie KIS). "
    "Tu es concis : pas de blabla, droit au but."
)


class DevState(TypedDict):
    task: str
    response: str


def call_claude(state: DevState) -> DevState:
    llm = ChatAnthropic(model=MODEL, max_tokens=2048)
    message = llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("user", state["task"]),
        ]
    )
    return {"task": state["task"], "response": message.content}


def build_dev_graph():
    graph = StateGraph(DevState)
    graph.add_node("call_claude", call_claude)
    graph.add_edge(START, "call_claude")
    graph.add_edge("call_claude", END)
    return graph.compile()
