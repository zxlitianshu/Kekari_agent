from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage
import json
import re

def planning_node(state):
    user_query = state["messages"][-1].content
    messages = state.get("messages", [])
    search_results = state.get("search_results", [])
    
    # Debug logging
    print(f"🔍 Debug - Search results type: {type(search_results)}")
    print(f"🔍 Debug - Search results length: {len(search_results) if search_results else 0}")
    print(f"🔍 Debug - Search results content: {search_results[:2] if search_results else 'None'}")
    
    # NEW: Check for compound requests (confirmation + new modification)
    compound_confirmation_keywords = [
        'this one is good', 'keep it', 'yes', 'incorporate', 'use it', 'save it',
        'good', 'perfect', 'nice', 'great', 'awesome', 'love it'
    ]
    
    compound_modification_keywords = [
        'make another', 'create another', 'do another', 'modify another', 'change another',
        'and i want', 'also want', 'also make', 'also create', 'also modify',
        'next one', 'another one', 'different style', 'different scene'
    ]
    
    # Check if this is a compound request
    is_compound_confirmation = any(keyword in user_query.lower() for keyword in compound_confirmation_keywords)
    is_compound_modification = any(keyword in user_query.lower() for keyword in compound_modification_keywords)
    
    if is_compound_confirmation and is_compound_modification and state.get("awaiting_confirmation", False):
        print(f"[Planning Node] Compound request detected: confirmation + new modification")
        print(f"[Planning Node] User query: '{user_query}'")
        
        # Extract the new modification instruction
        # Look for patterns like "and i want to make another one, [instruction]"
        modification_patterns = [
            r'and i want to make another one[,\s]+(.+)',
            r'also want to make another[,\s]+(.+)',
            r'make another one[,\s]+(.+)',
            r'create another[,\s]+(.+)',
            r'do another[,\s]+(.+)',
            r'and i want[,\s]+(.+)',
            r'also want[,\s]+(.+)'
        ]
        
        new_instruction = None
        for pattern in modification_patterns:
            match = re.search(pattern, user_query, re.IGNORECASE)
            if match:
                new_instruction = match.group(1).strip()
                break
        
        if new_instruction:
            print(f"[Planning Node] Extracted new instruction: '{new_instruction}'")
            
            # Set up the new image modification request
            state["image_modification_request"] = {
                "instruction": new_instruction,
                "image_url": None  # Will be resolved in image_agent
            }
            state["plan_action"] = "image_agent"
            state["action_type"] = "image_modification"
            
            # Also mark that we should incorporate the previous modification
            state["incorporate_previous"] = True
            
            return state
    
    # NEW: Check for listing database operations
    listing_db_keywords = [
        'yes', 'yes, incorporate it', 'incorporate', 'add it', 'save it', 'use it',
        'no', 'no, keep original', 'discard', 'don\'t use', 'keep original',
        'view all listing', 'show listing', 'list ready', 'remove'
    ]
    
    # Check if user is responding to image modification confirmation
    is_listing_db_operation = any(keyword in user_query.lower() for keyword in listing_db_keywords)
    
    if is_listing_db_operation and state.get("awaiting_confirmation", False):
        print(f"[Planning Node] Listing database operation detected: '{user_query}'")
        state["plan_action"] = "listing_database"
        return state
    
    # Build full conversation history
    history = "\n".join([
        f"User: {m.content}" if isinstance(m, HumanMessage) else f"Assistant: {m.content}" for m in messages[:-1]
    ])
    
    # Summarize all previous search results
    results_summary = "; ".join([
        f"SKU: {p.get('metadata', {}).get('sku', '')}, Name: {p.get('metadata', {}).get('name', '')}" for p in search_results
    ])
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1, request_timeout=10)
    
    prompt = f"""You are a conversation router. Analyze the user's intent and route to the appropriate action.

CONVERSATION HISTORY:
{history}

PREVIOUSLY FOUND PRODUCTS:
{results_summary if results_summary else 'None'}

USER'S LATEST QUERY:
{user_query}

AVAILABLE ACTIONS:
1. "gpt4_chat" - General conversation, analysis, questions
2. "decide_search_strategy" - Find/search for products
3. "shopify_agent" - Publish products to Shopify
4. "image_agent" - Modify product images (background changes, style transformations, etc.)

ROUTING RULES:
- Use "decify_search_strategy" for product search requests
- Use "shopify_agent" for publishing to Shopify (requires search_results)
- Use "image_agent" for image modifications (requires search_results)
- Use "gpt4_chat" for everything else

Respond with ONLY: {{"action": "action_name"}}"""

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
        action = decision.get("action", "gpt4_chat")  # Default to gpt4_chat instead of search
    except Exception as e:
        print(f"[Planning Node] JSON parsing error: {e}, defaulting to gpt4_chat")
        action = "gpt4_chat"  # Default to gpt4_chat on error
    
    print(f"[Planning Node] Routing to: {action}")
    
    if action == "gpt4_chat":
        state["plan_action"] = "gpt4_chat"
    elif action == "shopify_agent":
        # Check if we have search results before allowing Shopify publishing
        if not search_results:
            print("[Planning Node] No search results found, redirecting to gpt4_chat for Shopify request")
            state["plan_action"] = "gpt4_chat"
        else:
            print(f"[Planning Node] Found {len(search_results)} search results, proceeding to shopify_agent")
            state["plan_action"] = "shopify_agent"
            # Set action type for intent parser
            state["action_type"] = "shopify_listing"
    elif action == "image_agent":
        # Check if we have search results before allowing image modification
        if not search_results:
            print("[Planning Node] No search results found, redirecting to gpt4_chat for image modification request")
            state["plan_action"] = "gpt4_chat"
        else:
            print(f"[Planning Node] Found {len(search_results)} search results, proceeding to image_agent")
            state["plan_action"] = "image_agent"
            # Set up image modification request
            state["image_modification_request"] = {
                "instruction": user_query,
                "image_url": None  # Will be resolved in image_agent
            }
            # Set action type for intent parser
            state["action_type"] = "image_modification"
            print(f"[Planning Node] Set image_modification_request: {state['image_modification_request']}")
            print(f"[Planning Node] Set plan_action: {state['plan_action']}")
    else:
        state["plan_action"] = "decide_search_strategy"
    
    return state 