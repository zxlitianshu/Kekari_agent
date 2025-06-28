from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph_workflow.utils.helpers import detect_language

def gpt4_chat_node(state):
    user_query = state["messages"][-1].content
    messages = state.get("messages", [])
    search_results = state.get("search_results", [])
    language = state.get("language", "en")  # Get language from state
    
    # NEW: Get image modification results
    modified_images = state.get("modified_images", [])
    image_agent_response = state.get("image_agent_response", "")
    awaiting_confirmation = state.get("awaiting_confirmation", False)
    
    # NEW: Get listing database results
    listing_database_response = state.get("listing_database_response", "")
    listing_ready_products = state.get("listing_ready_products", [])
    
    # NEW: Automatically add search results to listing database if they don't exist
    if search_results and not listing_database_response:
        from .listing_database import ListingDatabase
        db = ListingDatabase()
        
        # Add search results to listing database
        added_skus = db.add_multiple_products_from_search(search_results)
        if added_skus:
            print(f"📋 Auto-added {len(added_skus)} products to listing database: {added_skus}")
            # Update listing_ready_products in state
            listing_ready_products = db.list_products()
    
    print(f"🔍 GPT Chat Node - Language from state: {language}")
    
    # Fallback: detect language if not in state
    if language == "en":
        print(f"🔍 GPT Chat Node - Language was 'en', detecting from user query...")
        language = detect_language(user_query)
    
    print(f"🌐 GPT Chat Node - Final detected language: {language}")
    
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
    
    # NEW: Build context from modified images
    modified_images_context = ""
    if modified_images:
        print(f"🎨 Debug - Found {len(modified_images)} modified images")
        modified_images_context = "\n\nRECENTLY MODIFIED IMAGES:\n"
        for i, img_result in enumerate(modified_images, 1):
            if img_result.get('status') == 'success':
                modified_images_context += f"{i}. SKU: {img_result.get('sku', 'N/A')}\n"
                modified_images_context += f"   Original Image: {img_result.get('original_image_url', 'N/A')}\n"
                modified_images_context += f"   Modified Image: {img_result.get('modified_image_url', 'N/A')}\n"
                modified_images_context += f"   Instruction: {img_result.get('instruction', 'N/A')}\n\n"
            else:
                modified_images_context += f"{i}. SKU: {img_result.get('sku', 'N/A')} - FAILED: {img_result.get('error', 'Unknown error')}\n\n"
    
    # NEW: Build context from listing database
    listing_db_context = ""
    if listing_ready_products:
        print(f"📋 Debug - Found {len(listing_ready_products)} listing-ready products")
        listing_db_context = "\n\nLISTING-READY PRODUCTS:\n"
        for i, sku in enumerate(listing_ready_products, 1):
            listing_db_context += f"{i}. SKU: {sku}\n"
    
    # NEW: Check if we have a direct response from image agent or listing database
    if image_agent_response and awaiting_confirmation:
        # User is being asked to confirm image modification
        return {"messages": [AIMessage(content=image_agent_response)]}
    
    if listing_database_response:
        # User has interacted with listing database
        return {"messages": [AIMessage(content=listing_database_response)]}
    
    # Create comprehensive prompt with language-specific instructions
    base_prompt = f"""You are a helpful AI assistant. Answer the user's current question directly, confidently, and naturally.

CONVERSATION HISTORY:
{history if history else "No previous conversation history."}

{products_context}

{modified_images_context}

{listing_db_context}

IMAGE AGENT RESPONSE:
{image_agent_response if image_agent_response else "No image modifications performed."}

LISTING DATABASE RESPONSE:
{listing_database_response if listing_database_response else "No listing database operations performed."}

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
- NEW: If the user asks about image modifications, refer to the "RECENTLY MODIFIED IMAGES" section above.
- NEW: When discussing modified images, always include both the original and modified image URLs.
- NEW: If image modification was successful, mention the new image URL and what changes were made.
- NEW: If image modification failed, explain what went wrong and suggest alternatives.
- NEW: All found products are automatically added to the listing database for easy Shopify publishing.
- NEW: Inform users they can list products immediately or modify images first.

INSTRUCTIONS:
- Answer the user's current question directly, confidently, and naturally.
- If they ask about conversation history, reference the history above.
- If they ask about products, use ONLY the product information above to make recommendations.
- If they ask about image modifications, reference the modified images section above.
- If they ask about listing products, inform them about the listing database.
- Be conversational, helpful, and a little witty or clever if appropriate.
- If the user asks for products but none are available, say "I don't have any products to show you right now."
- When discussing products, always include their exact SKU, key features, and image URLs from the metadata.
- When discussing modified images, include both original and modified image URLs.
- Format image links as: [Product Name](image_url) or simply include the full URL.
- Do NOT say you cannot provide image links—they are available in the context above.
- Think deeply: explain why a product is a great fit, how it could be used, or what makes it special.
- Be creative and insightful—connect the product's features to the user's needs.
- Speak with confidence: "This would be a great fit for you because..."
- Avoid hedging or apologizing. Don't say "maybe," "possibly," or "if it's not what you want."
- Never hallucinate or invent conversation topics that weren't actually discussed.
- IMPORTANT: If the user asks about a specific product attribute (like dimensions, material, color) that is not in the provided metadata, say "That specific information is not available in the product data I have."
- When describing products, be comprehensive and mention ALL relevant details from the metadata, including construction materials, features, and specifications.
- NEW: Always mention that products are ready for listing and suggest next steps.

NEXT STEPS SUGGESTIONS:
- If products are found: "These products are now in your listing database. You can: 1) List them on Shopify immediately, 2) Modify their images first, or 3) Search for more products."
- If image modifications are shown: "The modified image is ready. Would you like to incorporate it into the listing database?"
- If listing database has products: "You have products ready for listing. Use 'List on Shopify' to publish them."

Please respond to the user's query using ONLY the information provided above:"""

    # Add language-specific instruction
    if language == "zh-cn":
        prompt = base_prompt + "\n\nIMPORTANT: Respond in Chinese (中文)."
    else:
        prompt = base_prompt + "\n\nIMPORTANT: Respond in English."

    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    response = llm.invoke(prompt)
    
    return {"messages": [AIMessage(content=response.content)]} 