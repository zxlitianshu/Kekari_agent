"""
Standalone Image Agent for direct image upload and editing
This agent works independently of the product search workflow.
"""

import os
import time
import json
import tempfile
import requests
from typing import Dict, List, Optional
from langchain.schema import AIMessage, HumanMessage
from .image_agent import ImageAgent, generate_replicate_prompt


def standalone_image_agent_node(state):
    """
    Standalone image agent for direct image upload and editing
    This handles cases where users just want to upload and edit images
    without being in the product search workflow.
    
    Expects state to contain:
    - uploaded_files: List of uploaded file info
    - user_query: The modification instruction
    
    Returns state with:
    - modified_images: List of modified image results
    - standalone_image_response: Summary of modifications
    """
    print("🔄 LangGraph: Executing 'standalone_image_agent' node...")
    
    # Initialize the image agent
    agent = ImageAgent()
    
    # Get uploaded files and user query
    uploaded_files = state.get("uploaded_files", [])
    user_query = state["messages"][-1].content
    
    print(f"🔍 Standalone Image Agent Debug - uploaded_files: {uploaded_files}")
    print(f"🔍 Standalone Image Agent Debug - user_query: {user_query}")
    
    # Check if we have uploaded files
    if not uploaded_files:
        return _request_file_upload_standalone(state, user_query)
    
    # Process the uploaded files
    return _process_uploaded_files_standalone(agent, state, uploaded_files, user_query)


def _request_file_upload_standalone(state: Dict, user_query: str) -> Dict:
    """Ask user to upload images for standalone processing."""
    # Detect if user is speaking Chinese
    is_chinese = any('\u4e00' <= char <= '\u9fff' for char in user_query)
    
    if is_chinese:
        response_text = """🎨 **图片编辑请求**

我理解你想要编辑图片，但我需要你先上传图片文件。

**如何操作：**
1. 使用文件上传功能上传你的图片文件
2. 然后提供你的修改指令（例如："把背景改成咖啡店"）

**支持格式：** JPG、PNG、GIF、WebP
**最大文件大小：** 每张图片10MB

上传图片后，我会用AI驱动的图片修改技术按照你的指令处理它们！"""
    else:
        response_text = """🎨 **Image Editing Request**

I understand you want to edit images, but I need you to upload the image files first.

**How to proceed:**
1. Upload your image file(s) using the file upload feature
2. Then provide your modification instruction (e.g., "Change the background to a coffee shop")

**Supported formats:** JPG, PNG, GIF, WebP
**Max file size:** 10MB per image

Once you upload the images, I'll process them with your instruction using AI-powered image modification!"""
    
    return {
        **state,
        "modified_images": [],
        "standalone_image_response": response_text,
        "messages": state.get("messages", []) + [AIMessage(content=response_text)],
        "awaiting_confirmation": False
    }


def _process_uploaded_files_standalone(agent: ImageAgent, state: Dict, uploaded_files: List[Dict], user_query: str) -> Dict:
    """Process uploaded files for standalone image editing."""
    print(f"🎨 Standalone Image Agent: Processing {len(uploaded_files)} uploaded files")
    
    # Always use only the latest uploaded file, regardless of how many are sent
    if uploaded_files:
        # Sort by file creation time if available, else just take the last
        latest_file = uploaded_files[-1]
        uploaded_files = [latest_file]
        print(f"🎨 Standalone Image Agent: Using only the latest uploaded file: {latest_file.get('filename', 'unknown')}")
        # Update state to only keep the latest file for cleanup and downstream use
        state["uploaded_files"] = [latest_file]
    else:
        state["uploaded_files"] = []
    
    # Build conversation context for better prompt generation
    conversation_context = ""
    messages = state.get("messages", [])
    if len(messages) > 1:
        # Get the last few messages for context (excluding the current one)
        recent_messages = messages[-4:-1]  # Last 3 messages before current
        conversation_context = "\n".join([
            f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content[:200]}..."
            for msg in recent_messages
        ])
    
    # Generate enhanced prompt for Replicate
    enhanced_prompt = generate_replicate_prompt(user_query, conversation_context)
    print(f"🎨 Generated Replicate prompt: {enhanced_prompt}")
    
    modified_images = []
    total_files = len(uploaded_files)
    
    for i, file_info in enumerate(uploaded_files, 1):
        file_path = file_info.get("path")
        filename = file_info.get("filename", f"file_{i}")
        
        if not file_path or not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            continue
            
        print(f"🎨 Processing image {i}/{total_files}: {filename}")
        
        try:
            # Process the image using the same logic as the workflow image agent
            result = agent.image_processor.process_local_image(
                image_path=file_path,
                instruction=enhanced_prompt
            )
            
            if result and result.get("status") == "success":
                modified_image_url = result.get("modified_url")
                if modified_image_url:
                    modified_images.append({
                        "original_filename": filename,
                        "modified_image_url": modified_image_url,
                        "instruction": enhanced_prompt
                    })
                    print(f"✅ Completed image {i}/{total_files}")
                else:
                    print(f"❌ No modified image URL returned for {filename}")
            else:
                print(f"❌ Failed to process {filename}: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error processing {filename}: {str(e)}")
            continue
    
    # Generate response based on results
    if modified_images:
        response_text = f"""🎨 **图片处理完成！** 我已成功按照你的要求处理了图片。\n\n**处理结果：**\n"""
        for i, img in enumerate(modified_images, 1):
            response_text += f"""\n**图片 {i}：**\n- 原文件名：{img['original_filename']}\n- 修改说明：{img['instruction'][:100]}...\n- 处理结果：✅ 成功\n\n![修改后的图片]({img['modified_image_url']})\n"""
        
        response_text += f"""\n\n**处理完成！** 共处理了 {len(modified_images)} 张图片。\n"""
    else:
        response_text = "❌ 抱歉，图片处理失败。请检查图片格式是否正确，或稍后重试。"
    
    # Create response message
    response_message = AIMessage(content=response_text)
    
    # Update state
    state["messages"].append(response_message)
    state["modified_images"] = modified_images
    
    return state 