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

# Global storage for session-based conversation IDs
session_conversations = {}

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
async def openai_chat(request: ChatRequest, http_request: Request):
    # Force streaming compatibility
    print("🟡 Incoming ChatRequest:", request)
    
    # Extract session ID from headers or generate one
    session_id = None
    
    # Try to get session ID from common headers
    session_headers = [
        "X-Session-ID",
        "Session-ID", 
        "X-Client-ID",
        "Client-ID",
        "X-Request-ID",
        "Request-ID"
    ]
    
    for header_name in session_headers:
        if header_name in http_request.headers:
            session_id = http_request.headers[header_name]
            print(f"✅ Found session ID in header '{header_name}': {session_id}")
            break
    
    # If no session ID found, try to use client IP + User-Agent as session identifier
    if not session_id:
        client_ip = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("User-Agent", "unknown")
        session_id = f"{client_ip}-{user_agent[:50]}"  # Truncate User-Agent
        print(f"🆔 Generated session ID from client info: {session_id}")
    
    # Get or create conversation ID for this session
    if session_id in session_conversations:
        conversation_id = session_conversations[session_id]
        print(f"🔄 Using existing conversation for session: {conversation_id}")
    else:
        conversation_id = str(uuid.uuid4())
        session_conversations[session_id] = conversation_id
        print(f"🆕 Created new conversation for session: {conversation_id}")
    
    state = {
        "messages": [m.dict() for m in request.messages],
        "user_query": request.messages[-1].content if request.messages else "",
        "search_queries": [],
        "search_results": [],
        "final_summary": "",
        "language": "en",
        "use_metadata_filter": False,
        "metadata_filters": {},
    }

    try:
        result = graph.invoke(state, config={"configurable": {"thread_id": conversation_id}})
        messages = result.get("messages", [])
        reply = messages[-1].content.strip() if messages else "⚠️ LangGraph returned no messages."
        print("🟢 Final assistant reply:", reply)

        # Construct OpenAI-compatible streamed response
        def fake_stream():
            data = {
                "id": "chatcmpl-2025agent",
                "object": "chat.completion.chunk",
                "choices": [{
                    "delta": {"role": "assistant", "content": reply},
                    "index": 0,
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(data)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(fake_stream(), media_type="text/event-stream")

    except Exception as e:
        print("🔴 Error:", e)
        return JSONResponse({
            "error": str(e),
            "message": "❌ Backend failed"
        }, status_code=500)

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
            for session_id, conv_id in session_conversations.items()
        ],
        "total": len(session_conversations)
    })

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a specific session"""
    if session_id in session_conversations:
        del session_conversations[session_id]
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
    global session_conversations
    session_conversations.clear()
    print("🗑️ Cleared all sessions")
    return JSONResponse({
        "success": True,
        "message": "All sessions cleared"
    })
