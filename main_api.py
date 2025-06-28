from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from langgraph_workflow.graph_build import create_graph
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import config
import asyncio
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse
import json
import uuid
from uuid import uuid4
from langchain_core.messages import HumanMessage
import time

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown

app = FastAPI(lifespan=lifespan)

# Allow frontend to connect (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Only allow OpenWebUI frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "X-Requested-With"],
)

# # Add timeout middleware
# @app.middleware("http")
# async def timeout_middleware(request: Request, call_next):
#     try:
#         # Set timeout for the request processing
#         return await asyncio.wait_for(call_next(request), timeout=15.0)
#     except asyncio.TimeoutError:
#         return JSONResponse(
#             status_code=408,
#             content={"error": "Request timeout", "message": "The request took too long to process"}
#         )

graph = create_graph()

load_dotenv()

print("OPENAI_API_KEY loaded:", os.getenv("OPENAI_API_KEY"))

# Set OpenAI key
os.environ["OPENAI_API_KEY"] = config.OPENAI_API_KEY

# In-memory session store (for dev)
# session_store = {}
GLOBAL_STATE = None

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: bool = False

@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    user_message = data.get("message")
    session_id = data.get("session_id", "default")
    # Build the state for the graph
    state = {
        "messages": [],  # For now, start fresh each time
        "user_query": user_message,
        "search_queries": [],
        "search_results": [],
        "final_summary": "",
        "language": "en",
        "use_metadata_filter": False,
        "metadata_filters": {},
    }
    # Run the graph
    result = graph.invoke(state, config={"configurable": {"thread_id": session_id}})
    # Extract the assistant's reply
    reply = result["messages"][-1].content if result.get("messages") else ""
    return {"response": reply}

@app.post("/v1/chat/completions")
async def chat_endpoint(request: Request):
    global GLOBAL_STATE
    data = await request.json()
    user_query = data["messages"][-1]["content"]
    # Ignore session_id, use only one global state
    if GLOBAL_STATE is None:
        GLOBAL_STATE = {
            "messages": [],
            "user_query": "",
            "search_queries": [],
            "search_results": [],
            "final_summary": ""
        }
    state = GLOBAL_STATE
    state["messages"].append(HumanMessage(content=user_query))
    state["user_query"] = user_query
    prev_search_results = state.get("search_results", [])
    result = graph.invoke(state, config={"configurable": {"thread_id": "demo"}})
    if result.get("search_results"):
        state["search_results"] = result["search_results"]
    else:
        state["search_results"] = prev_search_results
    for k, v in result.items():
        if k != "search_results":
            state[k] = v
    GLOBAL_STATE = state  # Save back to global

    # Debug: Print all messages in result
    print("🔍 API Debug - All messages in result:")
    for i, m in enumerate(result["messages"]):
        print(f"{i}: {getattr(m, 'content', m)} (type: {getattr(m, 'type', None)}, role: {getattr(m, 'role', None)})")

    # Just return the last message in the list, regardless of type/role
    response_text = result["messages"][-1].content if result.get("messages") else ""
    def fake_stream():
        chunk = {
            "id": f"chatcmpl-demo",
            "object": "chat.completion.chunk",
            "choices": [{
                "delta": {"role": "assistant", "content": response_text},
                "index": 0,
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(fake_stream(), media_type="text/event-stream")

@app.get("/info")
async def info():
    return {
        "name": "My LangGraph Agent",
        "description": "A LangGraph-powered assistant.",
        "version": "1.0.0"
    }

@app.get("/v1/models")
def list_models():
    return JSONResponse({
        "object": "list",
        "data": [
            {
                "id": "2025agent",
                "object": "model",
                "created": 0,
                "owned_by": "you"
            }
        ]
    })

@app.get("/models")
def list_models_alias():
    return JSONResponse({
        "object": "list",
        "data": [
            {
                "id": "2025agent",
                "object": "model",
                "created": 0,
                "owned_by": "you"
            }
        ]
    })

@app.get("/v1/models/models")
def list_models_double_alias():
    return JSONResponse({
        "object": "list",
        "data": [
            {
                "id": "2025agent",
                "object": "model",
                "created": 0,
                "owned_by": "you"
            }
        ]
    })

@app.post("/openai/verify")
async def openai_verify(request: Request):
    # Accept and ignore any body
    return JSONResponse({"success": True, "message": "Connection verified."}) 

@app.post("/v1/followups")
def followups_stub():
    return {"questions": []}

# Add session management endpoints
@app.get("/sessions")
async def list_sessions():
    """List all active sessions and their conversation IDs"""
    return JSONResponse({
        "sessions": [
            {"session_id": session_id, "conversation_id": conv_id}
            for session_id, conv_id in session_store.items()
        ],
        "total": len(session_store)
    })

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a specific session"""
    if session_id in session_store:
        del session_store[session_id]
        print(f"🗑️ Deleted session: {session_id}")
        return JSONResponse({
            "success": True,
            "message": f"Session {session_id} deleted"
        })
    else:
        return JSONResponse({
            "success": False,
            "message": f"Session {session_id} not found"
        }, status_code=404)

@app.delete("/sessions")
async def clear_all_sessions():
    """Clear all sessions"""
    global session_store
    session_store.clear()
    print("🗑️ Cleared all sessions")
    return JSONResponse({
        "success": True,
        "message": "All sessions cleared"
    })
