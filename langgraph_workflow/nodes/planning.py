from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage
import json

def planning_node(state):
    user_query = state["messages"][-1].content
    messages = state.get("messages", [])
    search_results = state.get("search_results", [])
    
    # Debug logging
    print(f"🔍 Debug - Search results type: {type(search_results)}")
    print(f"🔍 Debug - Search results length: {len(search_results) if search_results else 0}")
    print(f"🔍 Debug - Search results content: {search_results[:2] if search_results else 'None'}")
    
    # CRITICAL FIX: If we have search results and this is a search query, 
    # route to gpt4_chat to generate a response instead of going back to search
    if search_results and any(keyword in user_query.lower() for keyword in ['find', 'search', 'recommend', 'show me', 'get me']):
        print(f"[Planning Node] Search results found ({len(search_results)} items), routing to gpt4_chat to generate response")
        state["plan_action"] = "gpt4_chat"
        return state
    
    # NEW FIX: If user mentions a specific SKU and we have search results, route directly to shopify_agent
    # This prevents the filter node from being called and potentially losing products
    if search_results:
        # Check if user mentioned a specific SKU
        sku_mentioned = None
        for product in search_results:
            sku = product.get('metadata', {}).get('sku', '')
            if sku and sku.lower() in user_query.lower():
                sku_mentioned = sku
                break
        
        # Check if user wants to list/publish products
        listing_keywords = ['list', 'publish', 'push', 'upload', 'make live', 'put on shopify', 'add to shopify']
        if any(keyword in user_query.lower() for keyword in listing_keywords):
            if sku_mentioned:
                print(f"[Planning Node] User mentioned specific SKU {sku_mentioned} and wants to list, routing directly to shopify_agent")
                state["plan_action"] = "shopify_agent"
                return state
            else:
                print(f"[Planning Node] User wants to list products but no specific SKU mentioned, routing to shopify_agent")
                state["plan_action"] = "shopify_agent"
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
    
    prompt = f"""You are an intelligent conversation router for an AI assistant. Your job is to analyze the conversation context and user intent to decide the best action.

CONVERSATION HISTORY:
{history}

PREVIOUSLY FOUND PRODUCTS:
{results_summary if results_summary else 'None'}

USER'S LATEST QUERY:
{user_query}

ANALYSIS TASK:
1. First, understand what the user is asking for by analyzing their query in context
2. Consider the conversation history - what have we discussed before?
3. Look at previously found products - are they relevant to this query?
4. Determine the user's intent: Are they asking for new information, referencing previous results, having a general conversation, or wanting to publish products to Shopify?

AVAILABLE ACTIONS:
1. "gpt4_chat" - Use for general conversation, questions, analysis, explanations, jokes, casual chat, or any non-product-related queries. This includes analyzing previously found products and general business discussions.
2. "decide_search_strategy" - Use when user asks to find, search, or recommend products/items/SKUs.
3. "shopify_agent" - Use when user wants to publish products to Shopify. This includes phrases like "push to shopify", "publish these", "make them live", "list on shopify", "put them on shopify", etc.

ROUTING RULES:
- Use "decide_search_strategy" when user wants to find products (any product search request)
- Use "shopify_agent" when user wants to publish existing products to Shopify (requires search_results to exist)
- Use "gpt4_chat" when user asks about previously found products or general analysis
- Use "gpt4_chat" for general conversation, market analysis, business advice
- Be smart about intent - if user wants products, route to search; if they want to publish, route to shopify

SHOPIFY PUBLISHING TRIGGERS:
- "push these to shopify"
- "publish these products"
- "make them live"
- "list on shopify"
- "put them on shopify"
- "upload to shopify"
- "publish to shopify"
- "go live with these"
- "make them available on shopify"

EXAMPLES:
- "Hello" → gpt4_chat
- "How are you?" → gpt4_chat  
- "Tell me a joke" → gpt4_chat
- "Analyze the market" → gpt4_chat
- "Find products for coffee shop" → decide_search_strategy
- "Find products suitable for outdoor spaces" → decide_search_strategy
- "Recommend items" → decide_search_strategy
- "Search for furniture" → decide_search_strategy
- "Tell me about those products" → gpt4_chat (analyzing previous products)
- "How do these items perform?" → gpt4_chat (analyzing previous products)
- "What's the market demand for these?" → gpt4_chat (analyzing previous products)
- "Give me business advice" → gpt4_chat (general business discussion)
- "Push these to Shopify" → shopify_agent
- "Publish these products" → shopify_agent
- "Make them live on Shopify" → shopify_agent
- "List these on Shopify" → shopify_agent

IMPORTANT: Only route to "shopify_agent" if there are search_results available (products found from previous searches).

Respond with ONLY the JSON: {{"action": "action_name"}}"""

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
    else:
        state["plan_action"] = "decide_search_strategy"
    
    return state 