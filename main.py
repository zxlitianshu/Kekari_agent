# main.py
import os
import config
from langgraph_workflow.graph_build import create_graph
from langchain_core.messages import HumanMessage
import uuid

# Set OpenAI key
os.environ["OPENAI_API_KEY"] = config.OPENAI_API_KEY

# Create LangGraph
graph = create_graph()

# Visualize graph
from IPython.display import Image, display

try:
    display(Image(graph.get_graph().draw_mermaid_png()))
except Exception:
    # This requires some extra dependencies and is optional
    pass

def chat(session_id=None):
    print("Type 'exit' or 'quit' to end the conversation.")
    if session_id is None:
        session_id = str(uuid.uuid4())
        print(f"[Session ID: {session_id}]")
    else:
        print(f"[Using Session ID: {session_id}]")
    
    # Initialize state once, outside the loop
    state = {
        "messages": [],
        "user_query": "",
        "search_queries": [],
        "search_results": [],
        "final_summary": ""
    }
    
    while True:
        user_query = input("You: ")
        if user_query.strip().lower() in ["exit", "quit"]:
            print("Exiting chat.")
            break
        
        # Update state with new message and query, but preserve other state data
        state["messages"].append(HumanMessage(content=user_query))
        state["user_query"] = user_query
        
        # Save previous search_results in case the new turn doesn't generate any
        prev_search_results = state.get("search_results", [])
        
        # Use session_id to persist memory for this user
        result = graph.invoke(state, config={"configurable": {"thread_id": session_id}})
        
        # If the new result has empty search_results, keep the previous ones
        if result.get("search_results"):
            state["search_results"] = result["search_results"]
        else:
            state["search_results"] = prev_search_results
        
        # Update other state keys
        for k, v in result.items():
            if k != "search_results":
                state[k] = v
        
        response = result["messages"][-1].content
        print("Assistant:", response)
        # Optionally, update messages with assistant's reply if you want to keep full history
        # from langchain_core.messages import AIMessage
        # state["messages"].append(AIMessage(content=response))

if __name__ == "__main__":
    import sys
    session_id = sys.argv[1] if len(sys.argv) > 1 else None
    chat(session_id)