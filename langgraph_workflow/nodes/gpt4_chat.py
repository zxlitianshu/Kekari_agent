from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage

def gpt4_chat_node(state):
    user_query = state["messages"][-1].content
    messages = state.get("messages", [])
    search_results = state.get("search_results", [])
    
    # Build conversation history - include all previous messages in this conversation
    history_messages = []
    for m in messages[:-1]:  # All messages except the current one
        if isinstance(m, HumanMessage):
            history_messages.append(f"User: {m.content}")
        else:
            history_messages.append(f"Assistant: {m.content}")
    
    history = "\n".join(history_messages)
    
    # Debug: Show conversation history
    print(f"🔍 Debug - Conversation history length: {len(messages[:-1])} messages")
    if len(messages[:-1]) > 0:
        print(f"🔍 Debug - First message: {messages[0].content[:100]}...")
        print(f"🔍 Debug - Last message: {messages[-2].content[:100]}...")
    else:
        print("🔍 Debug - No conversation history found")
    
    # Build context from previously found products
    products_context = ""
    if search_results:
        print(f"🔍 Debug - Found {len(search_results)} products in search_results")
        
        # Show full metadata structure for first product
        if search_results:
            first_product = search_results[0]
            metadata = first_product.get('metadata', {})
            print(f"🔍 Debug - First product metadata keys: {list(metadata.keys())}")
            print(f"🔍 Debug - First product full metadata: {metadata}")
        
        products_context = "\n\nPREVIOUSLY FOUND PRODUCTS:\n"
        for i, product in enumerate(search_results, 1):
            metadata = product.get('metadata', {})
            image_url = (metadata.get('main_image_url') or 
                        metadata.get('image_url') or 
                        metadata.get('image') or 
                        'N/A')
            products_context += f"{i}. SKU: {metadata.get('sku', 'N/A')}\n"
            products_context += f"   Category: {metadata.get('category', 'N/A')}\n"
            products_context += f"   Color: {metadata.get('color', 'N/A')}\n"
            products_context += f"   Material: {metadata.get('material', 'N/A')}\n"
            products_context += f"   Features: {metadata.get('characteristics_text', 'N/A')}\n"
            products_context += f"   Scene: {metadata.get('scene', 'N/A')}\n"
            products_context += f"   Image: {image_url}\n\n"
    else:
        print("🔍 Debug - No search_results found")
    
    # Create comprehensive prompt
    prompt = f"""You are a helpful AI assistant. Answer the user's current question directly, confidently, and naturally.

CONVERSATION HISTORY:
{history if history else "No previous conversation history."}

{products_context}

USER'S CURRENT QUERY:
{user_query}

INSTRUCTIONS:
- Answer the user's current question directly, confidently, and naturally.
- If they ask about conversation history, reference the history above.
- If they ask about products, use the product information above to make strong, positive recommendations.
- Be conversational, helpful, and a little witty or clever if appropriate.
- If the user asks for products but none are available, say "I don't have any products to show you right now."
- When discussing products, always include their SKU, key features, and image URLs.
- Format image links as: [Product Name](image_url) or simply include the full URL.
- Do NOT say you cannot provide image links—they are available in the context above.
- Think deeply: explain why a product is a great fit, how it could be used, or what makes it special.
- Be creative and insightful—connect the product's features to the user's needs.
- Speak with confidence: "This would be a great fit for you because..."
- Avoid hedging or apologizing. Don't say "maybe," "possibly," or "if it's not what you want."
- Never hallucinate or invent conversation topics that weren't actually discussed.

Please respond to the user's query:"""

    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    response = llm.invoke(prompt)
    
    return {"messages": [HumanMessage(content=response.content)]} 