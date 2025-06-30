from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage
import json
import re

def extract_text_from_multimodal_content(content):
    """Extract text content from multimodal messages, handling images properly."""
    if isinstance(content, str):
        return content
    
    if isinstance(content, list):
        text_parts = []
        image_count = 0
        
        for item in content:
            if item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif item.get("type") == "image_url":
                image_count += 1
        
        # Combine text parts
        text_content = " ".join(text_parts)
        
        # Add image indicator if images are present
        if image_count > 0:
            text_content += f" [User has uploaded {image_count} image(s)]"
        
        return text_content
    
    return str(content)

def planning_node(state):
    # Get the last message and extract text properly
    last_message = state["messages"][-1]
    user_query = extract_text_from_multimodal_content(last_message.content)
    
    messages = state.get("messages", [])
    search_results = state.get("search_results", [])
    uploaded_files = state.get("uploaded_files", [])
    awaiting_confirmation = state.get("awaiting_confirmation", False)
    
    # Debug logging
    print(f"🔍 Debug - Processed user query: {user_query[:100]}...")
    print(f"🔍 Debug - Search results length: {len(search_results) if search_results else 0}")
    print(f"🔍 Debug - Uploaded files: {len(uploaded_files) if uploaded_files else 0}")
    print(f"🔍 Debug - Awaiting confirmation: {awaiting_confirmation}")
    
    # Additional debug for search results
    if search_results:
        print(f"🔍 Debug - Search results SKUs: {[p.get('metadata', {}).get('sku', 'N/A') for p in search_results]}")
    else:
        print(f"🔍 Debug - No search results found in state")
    
    # PRIORITY: If awaiting confirmation, route to listing_database
    if awaiting_confirmation:
        print(f"[Planning Node] User is confirming image modification, routing to listing_database")
        state["plan_action"] = "listing_database"
        return state
    
    # PRIORITY: If user has uploaded files and wants image editing, route to standalone_image_agent
    if uploaded_files and any(keyword in user_query.lower() for keyword in ['edit', 'modify', 'change', 'background', 'transform', 'enhance', 'improve', '修改', '编辑', '改变', '背景', '变换', '增强', '改进']):
        print(f"[Planning Node] User uploaded files and wants image editing, routing to standalone_image_agent")
        state["plan_action"] = "standalone_image_agent"
        return state
    
    # PRIORITY: If user has uploaded files but no clear editing intent, ask for clarification
    if uploaded_files:
        print(f"[Planning Node] User uploaded files but unclear intent, asking for clarification")
        state["plan_action"] = "standalone_image_agent"
        return state
    
    # Check if images are present in the message
    has_images = False
    if isinstance(last_message.content, list):
        for item in last_message.content:
            if item.get("type") == "image_url":
                has_images = True
                break
    
    # Build full conversation history (without base64 data)
    history_parts = []
    for m in messages[:-1]:
        if isinstance(m, HumanMessage):
            content = extract_text_from_multimodal_content(m.content)
            history_parts.append(f"User: {content}")
        else:
            history_parts.append(f"Assistant: {m.content}")
    
    history = "\n".join(history_parts)
    
    # Summarize all previous search results
    results_summary = "; ".join([
        f"SKU: {p.get('metadata', {}).get('sku', '')}, Name: {p.get('metadata', {}).get('name', '')}" for p in search_results
    ])
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1, request_timeout=10)
    
    # Simplified LLM-based routing prompt
    prompt = f"""You are an intelligent conversation router that understands user intent and directs them to the appropriate service. Analyze the user's natural language request and determine what they want to accomplish.

CONVERSATION HISTORY:
{history}

PREVIOUSLY FOUND PRODUCTS:
{results_summary if results_summary else 'None'}

USER'S LATEST QUERY:
{user_query}

IMAGES PRESENT: {'Yes' if has_images else 'No'}
UPLOADED FILES: {'Yes' if uploaded_files else 'No'}

AVAILABLE SERVICES:
1. "gpt4_chat" - General conversation, questions, explanations, analysis
2. "decide_search_strategy" - Product discovery, searching, finding items
3. "shopify_agent" - Publishing products to Shopify store
4. "image_agent" - Modifying existing product images (backgrounds, scenes, styles)
5. "standalone_image_agent" - Processing uploaded images for editing

INTENT ANALYSIS:
**Product Discovery Intent**: User wants to find, search for, or discover products
- Natural language patterns: "find", "search", "look for", "show me", "get", "need", "want", "find me", "I'm looking for"
- Examples: "find chairs", "search for tables", "show me outdoor furniture", "I need a desk", "looking for lighting"

**Publishing Intent**: User wants to publish, list, or add products to their store
- Natural language patterns: "list", "publish", "add to store", "put on shopify", "upload to shopify", "create listing", "make live"
- Examples: "list this product", "publish to shopify", "add to my store", "make it live"

**Image Modification Intent**: User wants to change, modify, or enhance product images
- Natural language patterns: "modify", "change", "edit", "update", "enhance", "improve", "transform", "put in", "add background"
- Examples: "put this chair in a coffee shop", "change the background", "make it look more modern"

**Image Upload Intent**: User has uploaded files and wants to edit them
- Context: User has uploaded image files and wants to process them
- Examples: "edit this image", "modify this photo", "change the background of this"

**General Conversation Intent**: Everything else - questions, explanations, analysis
- Natural language patterns: "what is", "how does", "explain", "tell me about", "why", "when", "where"
- Examples: "what is this product made of?", "how does this work?", "explain the features"

ROUTING DECISION:
Based on the user's intent, route to the most appropriate service. Consider:
- What is the user trying to accomplish?
- What type of action do they want to take?
- What context clues indicate their intent?
- Are there any special circumstances (uploaded files, awaiting confirmation)?

Respond with ONLY: {{"action": "service_name"}}"""

    response = llm.invoke(prompt)
    
    # Debug: Show what the planning node received
    print(f"[Planning Node] Raw response: {response.content}")
    
    try:
        # Handle markdown-wrapped JSON responses
        content = response.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith('```'):
            # Find the JSON content between code blocks
            lines = content.split('\n')
            json_lines = []
            in_json = False
            for line in lines:
                if line.strip() == '```' or line.strip() == '```json':
                    in_json = not in_json
                    continue
                if in_json:
                    json_lines.append(line)
            content = '\n'.join(json_lines)
        
        decision = json.loads(content)
        action = decision.get("action", "gpt4_chat")  # Default to gpt4_chat
    except Exception as e:
        print(f"[Planning Node] JSON parsing error: {e}, defaulting to gpt4_chat")
        action = "gpt4_chat"  # Default to gpt4_chat on error
    
    print(f"[Planning Node] Routing to: {action}")
    
    # Set up the appropriate action
    if action == "gpt4_chat":
        state["plan_action"] = "gpt4_chat"
    elif action == "shopify_agent":
        # Allow Shopify agent to run even without current search results
        # The Shopify agent can work with products from the listing database
        print(f"[Planning Node] Proceeding to shopify_agent")
        state["plan_action"] = "shopify_agent"
    elif action == "image_agent":
        print(f"[Planning Node] Proceeding to image_agent")
        state["plan_action"] = "image_agent"
        # Set up image modification request
        state["image_modification_request"] = {
            "instruction": user_query,
            "image_url": None  # Will be resolved in image_agent
        }
        print(f"[Planning Node] Set image_modification_request: {state['image_modification_request']}")
    elif action == "standalone_image_agent":
        print(f"[Planning Node] Proceeding to standalone_image_agent")
        state["plan_action"] = "standalone_image_agent"
    else:
        state["plan_action"] = "decide_search_strategy"
    
    return state 