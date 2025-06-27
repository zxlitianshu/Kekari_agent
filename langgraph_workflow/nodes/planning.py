from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage
import json

def planning_node(state):
    user_query = state["messages"][-1].content
    messages = state.get("messages", [])
    search_results = state.get("search_results", [])
    
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
4. Determine the user's intent: Are they asking for new information, referencing previous results, or having a general conversation?

AVAILABLE ACTIONS:
1. "gpt4_chat" - Use for general conversation, questions, analysis, explanations, jokes, casual chat, or any non-product-related queries. This includes analyzing previously found products and general business discussions.
2. "decide_search_strategy" - Use when user asks to find, search, or recommend products/items/SKUs.

ROUTING RULES:
- Use "decide_search_strategy" when user wants to find products (any product search request)
- Use "gpt4_chat" when user asks about previously found products or general analysis
- Use "gpt4_chat" for general conversation, market analysis, business advice
- Be smart about intent - if user wants products, route to search

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
    else:
        state["plan_action"] = "decide_search_strategy"
    
    return state 