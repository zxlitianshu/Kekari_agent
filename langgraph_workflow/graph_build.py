# langgraph_workflow/graph_build.py

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver

# Import all node functions
from .nodes.rag_search import rag_search_node
from .nodes.metadata_filter_search import metadata_filter_search_node
from .nodes.planning import planning_node
from .nodes.gpt4_chat import gpt4_chat_node
from .nodes.shopify_agent import shopify_agent_node
from .nodes.filter_search_results import filter_search_results_node

# Define the LangGraph state
class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    user_query: str
    search_queries: list
    search_results: list
    final_summary: str
    language: str
    use_metadata_filter: bool
    metadata_filters: dict
    # NEW FIELDS FOR SHOPIFY AGENT
    shopify_products: list
    shopify_status: dict

# Decision node: Should we use metadata filter search?
def decide_search_strategy_node(state: GraphState):
    messages = state["messages"]
    history = "\n".join([
        f"User: {m.content}" if hasattr(m, 'content') else f"Assistant: {m.content}" for m in messages
    ])
    metadata_fields = [
         "category_code", "weight", "length", "width", "height", "weight_kg", "length_cm", "width_cm", "height_cm", "sku", "main_image_url", "US", "EU",  "material", "scene"
    ]
    from langchain_community.chat_models import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o")
    prompt = (
        f"Here is the full conversation so far:\n{history}\n\n"
        f"Available metadata fields: {metadata_fields}\n"
        "Based on the conversation, what is the user's current query and all relevant constraints (e.g., weight, category, etc.)?\n"
        "Return a JSON: {\"user_query\": string, \"use_metadata_filter\": true/false, \"filters\": {field: value, ...}}. "
        "If no metadata filter is needed, set use_metadata_filter to false and filters to an empty object."
    )
    response = llm.invoke(prompt)
    import json
    try:
        decision = json.loads(response.content)
    except Exception:
        decision = {"user_query": messages[-1].content, "use_metadata_filter": False, "filters": {}}
    return {
        **state,
        "user_query": decision.get("user_query", messages[-1].content),
        "use_metadata_filter": decision.get("use_metadata_filter", False),
        "metadata_filters": decision.get("filters", {})
    }

def create_graph():
    builder = StateGraph(GraphState)
    builder.add_node("planning", planning_node)
    builder.add_node("gpt4_chat", gpt4_chat_node)
    builder.add_node("decide_search_strategy", decide_search_strategy_node)
    builder.add_node("rag_search", rag_search_node)
    builder.add_node("metadata_filter_search", metadata_filter_search_node)
    builder.add_node("shopify_agent", shopify_agent_node)
    builder.add_node("filter_search_results", filter_search_results_node)
    
    # Planning node routes to gpt4_chat, decide_search_strategy, or shopify_agent
    def plan_route(state):
        plan_action = state.get("plan_action", "decide_search_strategy")
        if plan_action == "shopify_agent":
            return "shopify_agent"
        return plan_action
    
    builder.add_conditional_edges(
        "planning",
        plan_route,
        {
            "decide_search_strategy": "decide_search_strategy", 
            "gpt4_chat": "gpt4_chat",
            "shopify_agent": "shopify_agent"
        }
    )
    
    # Conditional routing based on use_metadata_filter
    def route_decision(state):
        return "metadata_filter_search" if state.get("use_metadata_filter") else "rag_search"
    
    builder.add_conditional_edges(
        "decide_search_strategy",
        route_decision,
        {"rag_search": "rag_search", "metadata_filter_search": "metadata_filter_search"}
    )
    
    # After rag_search or metadata_filter_search, go directly to gpt4_chat instead of planning
    builder.add_edge("rag_search", "gpt4_chat")
    builder.add_edge("metadata_filter_search", "gpt4_chat")
    
    # After gpt4_chat, end the workflow (no more routing)
    builder.add_edge("gpt4_chat", END)
    
    # After shopify_agent, end the workflow (no more routing)
    builder.add_edge("shopify_agent", END)
    
    # Set entry point to planning
    builder.set_entry_point("planning")
    saver = InMemorySaver()
    return builder.compile(checkpointer=saver)

# Expose the compiled graph for LangGraph CLI
graph = create_graph()
