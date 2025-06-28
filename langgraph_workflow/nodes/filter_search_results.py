from langchain_core.messages import HumanMessage
from langchain_community.chat_models import ChatOpenAI
import json

def filter_search_results_node(state):
    """
    Uses an LLM to filter search results based on user intent.
    For each selected product, also generates a compelling title and description.
    Returns only the most relevant product(s) for downstream actions.
    """
    user_query = state.get("user_query", "")
    search_results = state.get("search_results", [])
    messages = state.get("messages", [])
    if not search_results:
        return {**state}

    # Find the last assistant message (summary shown to user)
    last_assistant_message = ""
    for m in reversed(messages):
        if getattr(m, "type", None) == "ai" or getattr(m, "role", None) == "assistant":
            last_assistant_message = m.content
            break

    # Prepare a summary of each product for the LLM
    product_summaries = []
    for i, match in enumerate(search_results, 1):
        meta = match.get('metadata', {})
        summary = {
            "index": i,
            "sku": meta.get("sku", ""),
            "color": meta.get("color", ""),
            "category": meta.get("category", ""),
            "characteristics_text": meta.get("characteristics_text", ""),
            "main_image_url": meta.get("main_image_url", ""),
        }
        product_summaries.append(summary)

    llm = ChatOpenAI(model="gpt-4o", temperature=0.3, request_timeout=15)
    prompt = f"""
You are an expert e-commerce assistant. The user wants to list a product on Shopify.

Here is the last product summary you gave the user (if any):
{last_assistant_message}

Here are the candidate products:
{json.dumps(product_summaries, indent=2)}

User's instruction: {user_query}

IMPORTANT: Pay close attention to the user's specific request. If they mention:
- A specific color (like "khaki", "black", "white"), select the product with that exact color
- A specific material (like "rattan", "wood", "plastic"), select the product with that material
- A specific type (like "chair", "table", "seating"), select the product matching that type
- A specific SKU, select that exact product

1. Select the most relevant product(s) based on the user's instruction, the product details, and the last summary you gave.
2. For each selected product, generate a compelling, human-friendly product title and a rich, persuasive product description suitable for Shopify.
3. Return ONLY a JSON list of selected products, each with its SKU, and your generated title and description. Do not include any extra text or markdown.

Format:
[
  {{"sku": ..., "title": ..., "description": ...}}, ...
]
"""
    response = llm.invoke(prompt)
    try:
        content = response.content.strip()
        if content.startswith('```'):
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
        selected = json.loads(content)
    except Exception:
        selected = []

    # Attach generated title/description to the selected products' metadata
    filtered_results = []
    for sel in selected:
        sku = sel.get("sku")
        for match in search_results:
            meta = match.get('metadata', {})
            if meta.get("sku") == sku:
                # Overwrite or add title/description
                meta["title"] = sel.get("title", "")
                meta["description"] = sel.get("description", "")
                match["metadata"] = meta
                filtered_results.append(match)
                break

    # Debug: Print what the LLM selected
    print("🔍 Filter Node - LLM selected products:")
    for i, match in enumerate(filtered_results):
        meta = match.get('metadata', {})
        print(f"{i}: SKU={meta.get('sku', '')}, Title={meta.get('title', '')}, Description={meta.get('description', '')}")
    if not filtered_results:
        print("🔍 Filter Node - LLM did not select any products. Will fallback to top search result if available.")
    
    # Debug: Show all available products for comparison
    print("🔍 Filter Node - All available products:")
    for i, match in enumerate(search_results):
        meta = match.get('metadata', {})
        print(f"{i}: SKU={meta.get('sku', '')}, Color={meta.get('color', '')}, Category={meta.get('category', '')}")

    # Fallback: if LLM returns nothing, use the top search result and generate title/description with LLM
    if not filtered_results and search_results:
        match = search_results[0]
        meta = match.get('metadata', {})
        # Use LLM to generate a catchy title/description from metadata
        fallback_prompt = f"""
You are a product copywriter for an online store. Write a catchy, human-friendly product title and a rich, persuasive product description for Shopify, based on the following details:

User query: {user_query}
SKU: {meta.get('sku', '')}
Color: {meta.get('color', '')}
Category: {meta.get('category', '')}
Material: {meta.get('material', '')}
Features: {meta.get('characteristics_text', '')}

Return a JSON object: {{"title": ..., "description": ...}}
"""
        gen_response = llm.invoke(fallback_prompt)
        try:
            gen_json = json.loads(gen_response.content)
            meta['title'] = gen_json.get('title', meta.get('category', 'Product') + ' ' + meta.get('sku', ''))
            meta['description'] = gen_json.get('description', meta.get('characteristics_text', 'Great product.'))
        except Exception:
            meta['title'] = meta.get('category', 'Product') + ' ' + meta.get('sku', '')
            meta['description'] = meta.get('characteristics_text', 'Great product.')
        match['metadata'] = meta
        filtered_results = [match]
        print(f"🔍 Filter Node - Fallback to top product: SKU={meta.get('sku', '')}, Title={meta.get('title', '')}")

    return {
        **state,
        "search_results": filtered_results
    } 