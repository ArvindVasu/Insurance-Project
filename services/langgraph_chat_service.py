from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CHAT_DB = BASE_DIR / "chatbot.db"


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


_conn = sqlite3.connect(str(CHAT_DB), check_same_thread=False)
_checkpointer = SqliteSaver(conn=_conn)
_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)


def _chat_node(state: ChatState) -> ChatState:
    system_instruction = (
        "You are an underwriting assistant for insurance users. "
        "Give concise, practical, risk-aware answers."
    )
    messages = state["messages"]
    response = _llm.invoke([
        {"role": "system", "content": system_instruction},
        *messages,
    ])
    return {"messages": [response]}


def _build_graph():
    graph = StateGraph(ChatState)
    graph.add_node("chat_node", _chat_node)
    graph.add_edge(START, "chat_node")
    graph.add_edge("chat_node", END)
    return graph.compile(checkpointer=_checkpointer)


chatbot = _build_graph()


def list_threads() -> list[str]:
    threads: set[str] = set()
    for checkpoint in _checkpointer.list(None):
        thread_id = checkpoint.config.get("configurable", {}).get("thread_id")
        if thread_id:
            threads.add(thread_id)
    return sorted(threads, reverse=True)


def load_messages(thread_id: str) -> list[dict[str, str]]:
    config = {"configurable": {"thread_id": thread_id}}
    state = chatbot.get_state(config=config)
    if not state or not state.values.get("messages"):
        return []

    output: list[dict[str, str]] = []
    for msg in state.values["messages"]:
        role = "assistant"
        if isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        output.append({"role": role, "content": msg.content})
    return output


def stream_answer(thread_id: str, user_input: str):
    config = {"configurable": {"thread_id": thread_id}}
    for chunk, _meta in chatbot.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
        stream_mode="messages",
    ):
        if isinstance(chunk, AIMessage) and chunk.content:
            yield chunk.content

