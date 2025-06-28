from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

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
            if metadata.get('characteristics_text'):
                products_context += f"   Detailed Features: {metadata.get('characteristics_text')}\n"
            if metadata.get('height') or metadata.get('width') or metadata.get('length'):
                products_context += f"   Dimensions: Height: {metadata.get('height', 'N/A')}\", Width: {metadata.get('width', 'N/A')}\", Length: {metadata.get('length', 'N/A')}\"\n"
            if metadata.get('weight'):
                products_context += f"   Weight: {metadata.get('weight', 'N/A')} lbs\n"
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

CRITICAL INSTRUCTIONS:
- You MUST use ONLY the product information provided above. Do NOT invent or hallucinate any product details.
- If the user asks about specific products, refer ONLY to the products listed above with their exact SKU, color, material, and features.
- If the user asks for dimensions, materials, or other attributes, use ONLY what is provided in the product metadata above.
- If specific information (like dimensions) is not provided in the metadata, say "This information is not available in the product data."
- Do NOT make up colors, materials, or features that are not in the provided product data.
- When discussing products, always reference their exact SKU and use the exact color/material from the metadata.
- IMPORTANT: Use ALL available information from the product metadata, including the detailed "Features" section which contains comprehensive product descriptions.
- If the metadata includes "characteristics_text" or detailed feature descriptions, make sure to mention these specific details when relevant.
- Be thorough and detailed when describing products - use every piece of information available in the metadata.

INSTRUCTIONS:
- Answer the user's current question directly, confidently, and naturally.
- If they ask about conversation history, reference the history above.
- If they ask about products, use ONLY the product information above to make recommendations.
- Be conversational, helpful, and a little witty or clever if appropriate.
- If the user asks for products but none are available, say "I don't have any products to show you right now."
- When discussing products, always include their exact SKU, key features, and image URLs from the metadata.
- Format image links as: [Product Name](image_url) or simply include the full URL.
- Do NOT say you cannot provide image links—they are available in the context above.
- Think deeply: explain why a product is a great fit, how it could be used, or what makes it special.
- Be creative and insightful—connect the product's features to the user's needs.
- Speak with confidence: "This would be a great fit for you because..."
- Avoid hedging or apologizing. Don't say "maybe," "possibly," or "if it's not what you want."
- Never hallucinate or invent conversation topics that weren't actually discussed.
- IMPORTANT: If the user asks about a specific product attribute (like dimensions, material, color) that is not in the provided metadata, say "That specific information is not available in the product data I have."
- When describing products, be comprehensive and mention ALL relevant details from the metadata, including construction materials, features, and specifications.

Please respond to the user's query using ONLY the information provided above:"""

    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    response = llm.invoke(prompt)
    
    return {"messages": [AIMessage(content=response.content)]} 