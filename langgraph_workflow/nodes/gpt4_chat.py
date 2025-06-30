from langchain_community.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph_workflow.utils.helpers import detect_language

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

def gpt4_chat_node(state):
    # Extract text from multimodal content properly
    user_query = extract_text_from_multimodal_content(state["messages"][-1].content)
    
    # Get other state variables
    search_results = state.get("search_results", [])
    modified_images = state.get("modified_images", [])
    image_agent_response = state.get("image_agent_response", "")
    listing_database_response = state.get("listing_database_response", "")
    listing_ready_products = state.get("listing_ready_products", [])
    awaiting_confirmation = state.get("awaiting_confirmation", False)
    messages = state.get("messages", [])
    
    # Auto-add products to listing database if we have search results
    if search_results and not state.get("products_added_to_db", False):
        from .listing_database import ListingDatabase
        db = ListingDatabase()
        added_skus = db.add_multiple_products_from_search(search_results)
        print(f"📋 Auto-added {len(added_skus)} products to listing database: {added_skus}")
        state["products_added_to_db"] = True
    
    print(f"🔍 GPT Chat Node - User query: '{user_query}'")
    
    # Build conversation history - include all previous messages in this conversation (without base64 data)
    history_messages = []
    for m in messages[:-1]:  # All messages except the current one
        if isinstance(m, HumanMessage):
            content = extract_text_from_multimodal_content(m.content)
            history_messages.append(f"User: {content}")
        else:
            history_messages.append(f"Assistant: {m.content}")
    
    history = "\n".join(history_messages)
    
    # Debug: Show conversation history
    print(f"🔍 Debug - Conversation history length: {len(messages[:-1])} messages")
    if len(messages[:-1]) > 0:
        print(f"🔍 Debug - First message: {extract_text_from_multimodal_content(messages[0].content)[:100]}...")
        print(f"🔍 Debug - Last message: {extract_text_from_multimodal_content(messages[-2].content)[:100]}...")
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
        
        products_context = "\n\nFOUND PRODUCTS:\n"
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
    
    # Build context from modified images
    modified_images_context = ""
    if modified_images:
        print(f"🎨 Debug - Found {len(modified_images)} modified images")
        modified_images_context = "\n\nRECENTLY MODIFIED IMAGES:\n"
        for i, img_result in enumerate(modified_images, 1):
            if img_result.get('status') == 'success':
                modified_images_context += f"{i}. SKU: {img_result.get('sku', 'N/A')}\n"
                modified_images_context += f"   Original Image: {img_result.get('original_url', 'N/A')}\n"
                modified_images_context += f"   Modified Image: {img_result.get('modified_url', 'N/A')}\n"
                modified_images_context += f"   Instruction: {img_result.get('instruction', 'N/A')}\n\n"
            else:
                modified_images_context += f"{i}. SKU: {img_result.get('sku', 'N/A')} - FAILED: {img_result.get('error', 'Unknown error')}\n\n"
    
    # Build context from listing database
    listing_db_context = ""
    if listing_ready_products:
        print(f"📋 Debug - Found {len(listing_ready_products)} listing-ready products")
        listing_db_context = "\n\nLISTING-READY PRODUCTS:\n"
        for i, sku in enumerate(listing_ready_products, 1):
            listing_db_context += f"{i}. SKU: {sku}\n"
    
    # Check if we have a direct response from image agent or listing database
    if image_agent_response and awaiting_confirmation:
        # User is being asked to confirm image modification
        return {"messages": [AIMessage(content=image_agent_response)]}
    
    if listing_database_response:
        # User has interacted with listing database
        return {"messages": [AIMessage(content=listing_database_response)]}
    
    # If the last message is already from the assistant and contains image processing results,
    # don't generate a new response to avoid duplicates
    if messages and isinstance(messages[-1], AIMessage) and "Image Processing Complete" in messages[-1].content:
        print("🎨 GPT Chat Node: Last message already contains image processing results, skipping")
        return {"messages": []}  # Return empty to avoid duplicate
    
    # Create comprehensive prompt with language detection
    # Detect if user is speaking Chinese
    is_chinese = any('\u4e00' <= char <= '\u9fff' for char in user_query)
    language_instruction = "Respond in Chinese (中文)." if is_chinese else "Respond in English."
    
    prompt = f"""You are a helpful AI assistant. Answer the user's current question directly, confidently, and naturally.

{language_instruction}

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

INSTRUCTIONS:
- Answer the user's current question directly, confidently, and naturally.
- If they ask about conversation history, reference the history above.
- If they ask about products, use the product information above to make recommendations.
- If they ask about image modifications, reference the modified images section above.
- If they ask about listing products, inform them about the listing database.
- Be conversational, helpful, and a little witty or clever if appropriate.
- When discussing products, always include their exact SKU, key features, and DISPLAY the images using Markdown.
- When discussing modified images, include both original and modified image URLs using Markdown.
- Think deeply: explain why a product is a great fit, how it could be used, or what makes it special.
- Be creative and insightful—connect the product's features to the user's needs.
- Speak with confidence: "This would be a great fit for you because..."
- Avoid hedging or apologizing. Don't say "maybe," "possibly," or "if it's not what you want."
- Never hallucinate or invent conversation topics that weren't actually discussed.
- IMPORTANT: If the user asks about a specific product attribute (like dimensions, material, color) that is not in the provided metadata, say "That specific information is not available in the product data I have."
- When describing products, be comprehensive and mention ALL relevant details from the metadata, including construction materials, features, and specifications.
- Always mention that products are ready for listing and suggest next steps.

IMAGE FORMATTING INSTRUCTIONS:
- ALWAYS display product images using Markdown syntax: ![Product Name](image_url)
- For each product, show the main image prominently using the main_image_url from the product metadata
- When showing multiple products, organize them clearly with headers and proper spacing
- Use consistent formatting for all product displays
- Make sure images are displayed, not just linked as text

OUTPUT ORGANIZATION:
- Start with a brief summary of what you found
- For each product, use this format:
  **SKU:** [sku from metadata]
  ![Product Image]([main_image_url from metadata])
  **Category:** [category from metadata]
  **Color:** [color from metadata]
  **Material:** [material from metadata]
  **Weight:** [weight from metadata] lbs
  **Dimensions:** [dimensions from metadata]
  **Key Features:** [key_features from metadata]
  ---
- End with next steps and suggestions

NEXT STEPS SUGGESTIONS:
- If products are found: "These products are now in your listing database. You can: 1) List them on Shopify immediately, 2) Modify their images first, or 3) Search for more products."
- If image modifications are shown: "The modified image is ready. Would you like to incorporate it into the listing database?"
- If listing database has products: "You have products ready for listing. Use 'List on Shopify' to publish them."

Please respond to the user's query using the information provided above:"""

    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    response = llm.invoke(prompt)
    
    return {"messages": [AIMessage(content=response.content)]} 