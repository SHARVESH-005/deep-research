import os
import json
from typing import TypedDict, Annotated, List, Dict, Any
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from tavily import TavilyClient

from state import ResearchState

load_dotenv()

# Initialize LLM and Tavily
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=os.environ.get("GOOGLE_API_KEY"),
    temperature=0.2
)

tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

def planner_node(state: ResearchState) -> Dict[str, Any]:
    """Generates a research plan based on the user's query."""
    print("--- PLANNING ---")
    query = state["query"]
    
    system_prompt = """You are an expert research planner. 
    Given a user's research query, break it down into 2-3 specific, actionable search queries that will gather comprehensive information.
    Return ONLY a JSON array of strings, where each string is a search query.
    Example: ["What is X?", "Recent developments in X", "Pros and cons of X"]"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Query: {query}")
    ]
    
    response = llm.invoke(messages)
    
    try:
        # Extremely basic parsing - in production use structured output
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        plan = json.loads(content)
        if not isinstance(plan, list):
            plan = [query]
    except Exception as e:
        print(f"Error parsing plan: {e}")
        plan = [query] # fallback to original query
        
    return {"plan": plan, "status": "planning_complete"}

def searcher_node(state: ResearchState) -> Dict[str, Any]:
    """Executes the search plan using Tavily."""
    print("--- SEARCHING ---")
    plan = state.get("plan", [])
    
    all_results = []
    sources = []
    
    for search_query in plan:
        try:
            print(f"Searching for: {search_query}")
            # In a real app we'd use Redis caching here:
            # cached = redis.get(search_query) ...
            
            response = tavily_client.search(query=search_query, search_depth="advanced", max_results=3)
            
            for result in response.get("results", []):
                all_results.append({
                    "title": result.get("title"),
                    "content": result.get("content"),
                    "url": result.get("url")
                })
                sources.append({
                    "title": result.get("title"),
                    "url": result.get("url")
                })
        except Exception as e:
            print(f"Search error for '{search_query}': {e}")
            
    # Deduplicate sources based on URL
    unique_sources = []
    seen_urls = set()
    for s in sources:
        if s["url"] not in seen_urls:
            unique_sources.append(s)
            seen_urls.add(s["url"])
            
    return {"search_results": all_results, "sources": unique_sources, "status": "searching_complete"}

def synthesizer_node(state: ResearchState) -> Dict[str, Any]:
    """Synthesizes search results into a final report."""
    print("--- SYNTHESIZING ---")
    query = state["query"]
    results = state.get("search_results", [])
    
    context = ""
    for i, res in enumerate(results):
        context += f"Source [{i+1}] ({res['url']}):\n{res['content']}\n\n"
        
    system_prompt = """You are an expert research synthesizer.
    Write a comprehensive, well-structured report answering the user's query based ONLY on the provided context.
    Use Markdown formatting (headings, bullet points, etc.).
    CRITICAL: You must cite your sources inline using [1], [2], etc., corresponding to the Source index provided.
    Do not invent information. If the context doesn't contain the answer, state that.
    End the report with a '## Confidence Score' section, giving a score from 1-100 on how well the context answered the query."""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Query: {query}\n\nContext:\n{context}")
    ]
    
    response = llm.invoke(messages)
    
    # We could parse confidence score out, but for simplicity we leave it in the markdown
    return {"draft_report": response.content, "status": "done"}

# Build the graph
workflow = StateGraph(ResearchState)

workflow.add_node("planner", planner_node)
workflow.add_node("searcher", searcher_node)
workflow.add_node("synthesizer", synthesizer_node)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "searcher")
workflow.add_edge("searcher", "synthesizer")
workflow.add_edge("synthesizer", END)

research_graph = workflow.compile()
