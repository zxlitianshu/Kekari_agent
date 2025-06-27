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
    messages = []
    while True:
        user_query = input("You: ")
        if user_query.strip().lower() in ["exit", "quit"]:
            print("Exiting chat.")
            break
        messages.append(HumanMessage(content=user_query))
        state = {
            "messages": messages,
            "user_query": user_query,
            "search_queries": [],
            "search_results": [],
            "final_summary": ""
        }
        # Use session_id to persist memory for this user
        result = graph.invoke(state, config={"configurable": {"thread_id": session_id}})
        response = result["messages"][-1].content
        print("Assistant:", response)
        # Optionally, update messages with assistant's reply if you want to keep full history
        # from langchain_core.messages import AIMessage
        # messages.append(AIMessage(content=response))

if __name__ == "__main__":
    import sys
    session_id = sys.argv[1] if len(sys.argv) > 1 else None
    chat(session_id)