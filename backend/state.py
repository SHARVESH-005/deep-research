from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class ResearchState(TypedDict):
    query: str
    messages: Annotated[list[BaseMessage], add_messages]
    plan: List[str]
    current_step_idx: int
    search_results: List[Dict[str, Any]]
    draft_report: str
    confidence_score: float
    sources: List[Dict[str, str]]
    status: str # e.g. "planning", "searching", "synthesizing", "done"
