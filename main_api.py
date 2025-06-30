from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
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
from langchain_core.messages import HumanMessage, AIMessage
import time
import tempfile
import base64
from langchain_community.chat_models import ChatOpenAI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Backend starting up - clearing all session memory...")
    global session_store, GLOBAL_STATE
    session_store.clear()
    GLOBAL_STATE = None
    print("✅ All session memory cleared - starting fresh!")
    yield
    # Shutdown
    print("🛑 Backend shutting down...")

app = FastAPI(lifespan=lifespan)

# Allow frontend to connect (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000", "http://127.0.0.1:8080", "http://127.0.0.1:3000"],  # Allow OpenWebUI and other common ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "X-Requested-With", "Cache-Control", "Connection"],
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
session_store = {}
GLOBAL_STATE = None

def clear_session_memory():
    """Clear all session memory to start fresh."""
    global session_store, GLOBAL_STATE
    session_store.clear()
    GLOBAL_STATE = None
    print("🧹 Session memory cleared - starting fresh!")

class Message(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]  # Support both string and multimodal content

class ChatRequest(BaseModel):
    messages: List[Message]
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

def process_multimodal_content(content_list):
    """Process multimodal content, handling images properly to avoid token limits."""
    text_content = ""
    image_count = 0
    image_urls = []
    base64_images = []
    
    for content_item in content_list:
        if content_item.get("type") == "text":
            text_content += content_item.get("text", "")
        elif content_item.get("type") == "image_url":
            image_url = content_item.get("image_url", {}).get("url", "")
            if image_url:
                # Check if it's a base64 image
                if image_url.startswith("data:image/"):
                    # For base64 images, store them for processing
                    image_count += 1
                    base64_images.append(image_url)
                else:
                    # For regular URLs, include them
                    image_urls.append(image_url)
    
    # Add image information to text content
    if image_count > 0:
        if image_urls:
            # Both base64 and URLs
            image_info = f"\n[Images: {image_count} uploaded image(s) + {len(image_urls)} URL(s): {', '.join(image_urls)}]"
        else:
            # Only base64 images
            image_info = f"\n[Images: {image_count} uploaded image(s)]"
        text_content += image_info
    elif image_urls:
        # Only URLs
        image_info = f"\n[Images: {', '.join(image_urls)}]"
        text_content += image_info
    
    return text_content, image_count, image_urls, base64_images

def save_base64_images_to_session(base64_images, session_id):
    """Save base64 images as uploaded files in the session."""
    if not base64_images:
        return []
    
    uploaded_files = []
    temp_dir = tempfile.mkdtemp()
    
    for i, base64_data in enumerate(base64_images):
        try:
            # Extract the data part from base64 URL
            if base64_data.startswith("data:image/"):
                # Parse the data URL
                header, data = base64_data.split(",", 1)
                # Extract content type
                content_type = header.split(":")[1].split(";")[0]
                # Extract file extension
                ext = content_type.split("/")[1] if "/" in content_type else "jpg"
                
                # Decode base64 data
                image_data = base64.b64decode(data)
                
                # Create temporary file
                filename = f"uploaded_image_{i+1}.{ext}"
                temp_path = os.path.join(temp_dir, filename)
                
                with open(temp_path, "wb") as f:
                    f.write(image_data)
                
                uploaded_files.append({
                    "path": temp_path,
                    "filename": filename,
                    "content_type": content_type,
                    "size": len(image_data)
                })
                
                print(f"💾 Saved base64 image as: {temp_path}")
                
        except Exception as e:
            print(f"❌ Error saving base64 image: {e}")
    
    return uploaded_files

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
        # NEW FIELDS FOR SHOPIFY AGENT
        "shopify_products": [],
        "shopify_status": {},
        # NEW FIELDS FOR IMAGE AGENT
        "image_modification_request": {},
        "modified_images": [],
        "image_agent_response": "",
        "awaiting_confirmation": False,
        # NEW FIELDS FOR LISTING DATABASE
        "listing_database_response": "",
        "listing_ready_products": [],
        # NEW FIELDS FOR INTENT PARSER
        "parsed_intent": {},
        "action_type": "general",
        # NEW FIELD FOR COMPOUND REQUESTS
        "incorporate_previous": False,
    }
    # Run the graph
    result = graph.invoke(state, config={"configurable": {"thread_id": session_id}})
    # Extract the assistant's reply
    reply = result["messages"][-1].content if result.get("messages") else ""
    return {"response": reply}

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    """Main chat endpoint that handles both regular chat and image processing with streaming support."""
    try:
        # 🧹 CLEAR SESSION MEMORY - START FRESH EVERY TIME
        # clear_session_memory()
        
        # Extract messages and session info
        messages = []
        base64_images = []
        
        for msg in request.messages:
            if msg.role == "user":
                # Handle multimodal content
                if isinstance(msg.content, list):
                    # Process multimodal content properly
                    text_content, image_count, image_urls, msg_base64_images = process_multimodal_content(msg.content)
                    messages.append(HumanMessage(content=text_content))
                    base64_images.extend(msg_base64_images)
                else:
                    # Regular text content
                    messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
        
        session_id = request.session_id or "default"
        
        # Get or create session state
        if session_id not in session_store:
            session_store[session_id] = {
                "messages": [],
                "search_results": [],
                "parsed_intent": {},
                "image_modification_request": {},
                "modified_images": [],
                "awaiting_confirmation": False,
                "incorporate_previous": False,
                "uploaded_files": [],
                "action_type": "general",
            }
        
        session_state = session_store[session_id]
        
        # IMPORTANT: Clear uploaded files at the beginning of each request to prevent accumulation
        session_state["uploaded_files"] = []
        
        # Save base64 images as uploaded files (only from current request)
        if base64_images:
            new_uploaded_files = save_base64_images_to_session(base64_images, session_id)
            session_state["uploaded_files"] = new_uploaded_files  # Replace, don't extend
            print(f"📁 Added {len(new_uploaded_files)} uploaded files to session (current request only)")
        else:
            print(f"📁 No uploaded files in current request")
        
        # Add new message to session (append instead of overwrite)
        if session_state["messages"]:
            # Append only the new messages that aren't already in the session
            existing_messages = session_state["messages"]
            new_messages = []
            
            for msg in messages:
                # Check if this message is already in the session
                is_duplicate = False
                for existing_msg in existing_messages:
                    if (isinstance(msg, type(existing_msg)) and 
                        msg.content == existing_msg.content):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    new_messages.append(msg)
            
            # Append new messages to existing ones
            session_state["messages"].extend(new_messages)
        else:
            # First time, just set the messages
            session_state["messages"] = messages
        
        # Prepare state for LangGraph
        state = {
            "messages": session_state["messages"],
            "search_results": session_state.get("search_results", []),
            "parsed_intent": session_state.get("parsed_intent", {}),
            "image_modification_request": session_state.get("image_modification_request", {}),
            "modified_images": session_state.get("modified_images", []),
            "awaiting_confirmation": session_state.get("awaiting_confirmation", False),
            "incorporate_previous": session_state.get("incorporate_previous", False),
            "uploaded_files": session_state.get("uploaded_files", []),
            "action_type": session_state.get("action_type", "general"),
        }
        
        # Debug: Check what's in the state
        print(f"🔍 Debug - State uploaded_files count: {len(state.get('uploaded_files', []))}")
        print(f"🔍 Debug - Session uploaded_files count: {len(session_state.get('uploaded_files', []))}")
        
        # Run the graph
        result = graph.invoke(state, config={"configurable": {"thread_id": session_id}})
        
        # Update session state - preserve search_results if not returned by graph
        update_data = {
            "parsed_intent": result.get("parsed_intent", {}),
            "image_modification_request": result.get("image_modification_request", {}),
            "modified_images": result.get("modified_images", []),
            "awaiting_confirmation": result.get("awaiting_confirmation", False),
            "incorporate_previous": result.get("incorporate_previous", False),
            "uploaded_files": result.get("uploaded_files", []),
            "action_type": result.get("action_type", session_state.get("action_type", "general")),
        }
        
        # Always preserve search_results - only update if new ones are returned
        if "search_results" in result:
            update_data["search_results"] = result["search_results"]
            print(f"🔍 Session Update: Graph returned {len(result['search_results'])} search results")
        else:
            # Preserve existing search_results if not returned by graph
            existing_results = session_state.get("search_results", [])
            update_data["search_results"] = existing_results
            print(f"🔍 Session Update: Preserving {len(existing_results)} existing search results")
        
        session_store[session_id].update(update_data)
        
        # IMPORTANT: Clear uploaded files after processing to prevent accumulation
        session_store[session_id]["uploaded_files"] = []
        
        # Get the last AI message or use image agent response
        ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        
        # SIMPLE: Just return the last AI message from the graph
        if ai_messages:
            response_content = ai_messages[-1].content
            response_type = "ai_message"
        else:
            response_content = "I'm sorry, I couldn't generate a response."
            response_type = "error"
        
        # Debug logging
        print(f"🔍 API Debug - Response selection:")
        print(f"  - ai_messages count: {len(ai_messages)}")
        print(f"  - Selected response type: {response_type}")
        
        print(f"🔍 API Debug - All messages in result:")
        for i, msg in enumerate(result["messages"]):
            print(f"{i}: {msg.content[:100]}... (type: {type(msg).__name__}, role: {getattr(msg, 'role', None)})")
        
        # Check if Shopify agent has returned a specific response
        shopify_status = result.get("shopify_status")
        if shopify_status and shopify_status.get("message"):
            response_content = shopify_status["message"]
            response_type = "shopify_response"
        
        # Return streaming response
        async def generate_stream():
            # Send an immediate message so the frontend can show something
            response_id = f"chatcmpl-{uuid4().hex}"
            created_time = int(time.time())
            initial_chunk = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": "Homywork-Agent V3.6 AI助手",
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant", "content": "⏳ Processing started, please wait...\n"},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(initial_chunk)}\n\n"
            await asyncio.sleep(0.5)  # Give frontend time to show spinner

            # Stream content in chunks (fake streaming)
            words = response_content.split()
            for i, word in enumerate(words):
                content_chunk = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": "Homywork-Agent V3.6 AI助手",
                    "choices": [{
                        "index": 0,
                        "delta": {"content": word + (" " if i < len(words) - 1 else "")},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(content_chunk)}\n\n"
                await asyncio.sleep(0.05)

            # Send final chunk
            final_chunk = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": "Homywork-Agent V3.6 AI助手",
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
        
    except Exception as e:
        print(f"❌ Error in chat completions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/chat/completions/json")
async def chat_completions_json(request: ChatRequest):
    """JSON endpoint for chat completions with proper OpenAI-compatible format."""
    try:
        # Extract messages and session info
        messages = []
        base64_images = []
        
        for msg in request.messages:
            if msg.role == "user":
                # Handle multimodal content
                if isinstance(msg.content, list):
                    # Process multimodal content properly
                    text_content, image_count, image_urls, msg_base64_images = process_multimodal_content(msg.content)
                    messages.append(HumanMessage(content=text_content))
                    base64_images.extend(msg_base64_images)
                else:
                    # Regular text content
                    messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
        
        session_id = request.session_id or "default"
        
        # Get or create session state
        if session_id not in session_store:
            session_store[session_id] = {
                "messages": [],
                "search_results": [],
                "parsed_intent": {},
                "image_modification_request": {},
                "modified_images": [],
                "awaiting_confirmation": False,
                "incorporate_previous": False,
                "uploaded_files": [],
                "action_type": "general",
            }
        
        session_state = session_store[session_id]
        
        # IMPORTANT: Clear uploaded files at the beginning of each request to prevent accumulation
        session_state["uploaded_files"] = []
        
        # Save base64 images as uploaded files (only from current request)
        if base64_images:
            new_uploaded_files = save_base64_images_to_session(base64_images, session_id)
            session_state["uploaded_files"] = new_uploaded_files  # Replace, don't extend
            print(f"📁 Added {len(new_uploaded_files)} uploaded files to session (current request only)")
        else:
            print(f"📁 No uploaded files in current request")
        
        # Add new message to session (append instead of overwrite)
        if session_state["messages"]:
            # Append only the new messages that aren't already in the session
            existing_messages = session_state["messages"]
            new_messages = []
            
            for msg in messages:
                # Check if this message is already in the session
                is_duplicate = False
                for existing_msg in existing_messages:
                    if (isinstance(msg, type(existing_msg)) and 
                        msg.content == existing_msg.content):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    new_messages.append(msg)
            
            # Append new messages to existing ones
            session_state["messages"].extend(new_messages)
        else:
            # First time, just set the messages
            session_state["messages"] = messages
        
        # Prepare state for LangGraph
        state = {
            "messages": session_state["messages"],
            "search_results": session_state.get("search_results", []),
            "parsed_intent": session_state.get("parsed_intent", {}),
            "image_modification_request": session_state.get("image_modification_request", {}),
            "modified_images": session_state.get("modified_images", []),
            "awaiting_confirmation": session_state.get("awaiting_confirmation", False),
            "incorporate_previous": session_state.get("incorporate_previous", False),
            "uploaded_files": session_state.get("uploaded_files", []),
            "action_type": session_state.get("action_type", "general"),
        }
        
        # Debug: Check what's in the state
        print(f"🔍 Debug - State uploaded_files count: {len(state.get('uploaded_files', []))}")
        print(f"🔍 Debug - Session uploaded_files count: {len(session_state.get('uploaded_files', []))}")
        
        # Run the graph
        result = graph.invoke(state, config={"configurable": {"thread_id": session_id}})
        
        # Update session state - preserve search_results if not returned by graph
        update_data = {
            "parsed_intent": result.get("parsed_intent", {}),
            "image_modification_request": result.get("image_modification_request", {}),
            "modified_images": result.get("modified_images", []),
            "awaiting_confirmation": result.get("awaiting_confirmation", False),
            "incorporate_previous": result.get("incorporate_previous", False),
            "uploaded_files": result.get("uploaded_files", []),
            "action_type": result.get("action_type", session_state.get("action_type", "general")),
        }
        
        # Always preserve search_results - only update if new ones are returned
        if "search_results" in result:
            update_data["search_results"] = result["search_results"]
            print(f"🔍 Session Update: Graph returned {len(result['search_results'])} search results")
        else:
            # Preserve existing search_results if not returned by graph
            existing_results = session_state.get("search_results", [])
            update_data["search_results"] = existing_results
            print(f"🔍 Session Update: Preserving {len(existing_results)} existing search results")
        
        session_store[session_id].update(update_data)
        
        # IMPORTANT: Clear uploaded files after processing to prevent accumulation
        session_store[session_id]["uploaded_files"] = []
        
        # Get the last AI message or use image agent response
        ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        
        # SIMPLE: Just return the last AI message from the graph
        if ai_messages:
            response_content = ai_messages[-1].content
            response_type = "ai_message"
        else:
            response_content = "I'm sorry, I couldn't generate a response."
            response_type = "error"
        
        # Debug logging
        print(f"🔍 API Debug - Response selection:")
        print(f"  - ai_messages count: {len(ai_messages)}")
        print(f"  - Selected response type: {response_type}")
        
        print(f"🔍 API Debug - All messages in result:")
        for i, msg in enumerate(result["messages"]):
            print(f"{i}: {msg.content[:100]}... (type: {type(msg).__name__}, role: {getattr(msg, 'role', None)})")
        
        # Check if Shopify agent has returned a specific response
        shopify_status = result.get("shopify_status")
        if shopify_status and shopify_status.get("message"):
            response_content = shopify_status["message"]
            response_type = "shopify_response"
        
        # Return OpenAI-compatible JSON format
        return {
            "id": f"chatcmpl-{uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "Homywork-Agent V3.6 AI助手",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
        
    except Exception as e:
        print(f"❌ Error in chat completions JSON: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/upload-files")
async def upload_files(
    files: List[UploadFile] = File(...),
    session_id: str = Form(...)
):
    """Upload files for image processing."""
    try:
        # Ensure session exists
        if session_id not in session_store:
            session_store[session_id] = {
                "messages": [],
                "search_results": [],
                "parsed_intent": {},
                "image_modification_request": {},
                "modified_images": [],
                "awaiting_confirmation": False,
                "incorporate_previous": False,
                "uploaded_files": [],
                "action_type": "general",
            }
        
        # Save uploaded files to temporary directory
        uploaded_files = []
        temp_dir = tempfile.mkdtemp()
        
        for file in files:
            if file.content_type.startswith('image/'):
                # Create temporary file
                temp_path = os.path.join(temp_dir, file.filename)
                with open(temp_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                
                uploaded_files.append({
                    "path": temp_path,
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "size": len(content)
                })
        
        # Update session with uploaded files
        session_store[session_id]["uploaded_files"] = uploaded_files
        
        return {
            "success": True,
            "uploaded_files": len(uploaded_files),
            "session_id": session_id,
            "message": f"Successfully uploaded {len(uploaded_files)} image file(s)"
        }
        
    except Exception as e:
        print(f"❌ Error uploading files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/info")
async def info():
    return {
        "name": "My LangGraph Agent",
        "description": "A LangGraph-powered assistant with image modification and intent parsing capabilities.",
        "version": "1.0.0"
    }

@app.get("/v1/models")
async def list_models():
    """List available models (for compatibility with OpenAI API)."""
    return {
        "data": [
            {
                "id": "Homywork-Agent V3.6 AI助手",
                "object": "model",
                "created": 1234567890,
                "owned_by": "openai"
            }
        ],
        "object": "list"
    }

@app.get("/v1/models/models")
async def models_endpoint():
    """Alternative models endpoint."""
    return await list_models()

@app.options("/v1/chat/completions")
async def options_chat_completions():
    """Handle OPTIONS requests for CORS."""
    return {"status": "ok"}

@app.options("/v1/chat/completions/json")
async def options_chat_completions_json():
    """Handle OPTIONS requests for CORS for JSON endpoint."""
    return {"status": "ok"}

@app.options("/v1/models")
async def options_models():
    """Handle OPTIONS requests for CORS."""
    return {"status": "ok"}

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

@app.get("/test-stream")
async def test_stream():
    """Test endpoint to verify streaming is working."""
    async def generate_test_stream():
        for i in range(10):
            chunk = {
                "id": f"test-{uuid4().hex}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "test-model",
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": f"Chunk {i+1} "
                    },
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.5)
        
        # Final chunk
        final_chunk = {
            "id": f"test-{uuid4().hex}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "test-model",
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_test_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
