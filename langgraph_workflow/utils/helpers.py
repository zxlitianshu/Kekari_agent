from langchain_community.chat_models import ChatOpenAI
import openai
import config
from langdetect import detect

# Helper: Use GPT to generate search queries from user query
def generate_search_queries(user_query, n=2):
    # Use GPT-4o for better performance
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1, request_timeout=10)
    prompt = f"""You are a product search expert. The user wants to find products and has given this query: '{user_query}'

Your task is to generate {n} effective search terms (2-4 words each) that will help find the most relevant products.

IMPORTANT RULES:
1. Pay attention to the user's specific requirements (outdoor, indoor, color, material, weight, etc.)
2. If the user mentions "户外" (outdoor), use "outdoor" or "户外" in your search terms
3. If the user mentions "室内" (indoor), use "indoor" or "室内" in your search terms
4. Include key product characteristics like material, color, or category
5. Keep terms short but specific (2-4 words max)
6. Return exactly {n} search terms

Examples:
- User: "帮我看看有没有适合户外场景的产品" → ["outdoor products", "户外用品"]
- User: "找黑色的桌子" → ["black table", "黑色桌子"]
- User: "铝制户外家具" → ["aluminum outdoor furniture", "铝制户外家具"]

Return the search terms as a JSON array: ["term1", "term2"]"""

    response = llm.invoke(prompt)
    
    # Try to extract list from response
    try:
        # Look for JSON array pattern in response
        import re
        import json
        # Try to find JSON array
        json_match = re.search(r'\[.*?\]', response.content)
        if json_match:
            queries = json.loads(json_match.group())
            if isinstance(queries, list) and len(queries) > 0:
                return queries[:n]  # Limit to n queries
    except Exception as e:
        print(f"⚠️ JSON parsing failed: {e}")
    
    # Fallback: split by lines and clean up
    lines = [line.strip().strip('- ').strip('"').strip("'") for line in response.content.split('\n')]
    queries = [line for line in lines if line and len(line) > 2 and len(line) < 30]
    
    if not queries:
        # Last resort: use the original query
        print(f"⚠️ No queries generated, using original query: {user_query}")
        return [user_query]
    
    return queries[:n]

# Helper: Pinecone search for a query
def pinecone_search(query, top_k=3, filter=None):
    openai.api_key = config.OPENAI_API_KEY
    from pinecone import Pinecone
    pc = Pinecone(api_key=config.PINECONE_API_KEY)
    index = pc.Index(config.INDEX_NAME)
    # Embed query
    embedding_response = openai.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    )
    query_vector = embedding_response.data[0].embedding
    # Always filter to only non-image vectors (i.e., product/item vectors)
    combined_filter = {"type": {"$ne": "image"}}
    if filter:
        combined_filter = {"$and": [combined_filter, filter]}
    search_kwargs = dict(vector=query_vector, top_k=top_k, include_metadata=True, filter=combined_filter)
    results = index.query(**search_kwargs)
    return results['matches']

# Helper: Detect language
def detect_language(text):
    try:
        lang_code = detect(text)
        print(f"🔍 Language detection result: {lang_code} for text: {text[:50]}...")
        
        # Map language codes to our supported languages (Chinese and English only)
        if lang_code in ['zh', 'zh-cn', 'zh-tw', 'zh-hk']:
            final_lang = 'zh-cn'
            print(f"✅ Mapped {lang_code} to {final_lang}")
            return final_lang
        elif lang_code in ['en', 'en-us', 'en-gb']:
            final_lang = 'en'
            print(f"✅ Mapped {lang_code} to {final_lang}")
            return final_lang
        else:
            # For any other language, default to English
            print(f"⚠️ Unknown language code {lang_code}, defaulting to English")
            return 'en'
    except Exception as e:
        print(f"⚠️ Language detection failed: {e}")
        # Fallback: check for Chinese characters
        if any('\u4e00' <= char <= '\u9fff' for char in text):
            print(f"✅ Fallback: Detected Chinese characters, returning zh-cn")
            return 'zh-cn'
        print(f"⚠️ Fallback: No Chinese characters detected, returning en")
        return "en"

def slim_product(product):
    """Return a copy of the product with only the main image (or no images) for GPT summarization."""
    slim = product.copy()
    meta = slim.get('metadata', {}).copy()
    # Keep only the main image URL, or remove all images
    if 'main_image_url' in meta:
        meta['image_urls'] = [meta['main_image_url']]
    else:
        meta['image_urls'] = []
    slim['metadata'] = meta
    return slim

# Helper: Summarize results with GPT
def summarize_results(user_query, products, language=None):
    # Use GPT-4o for better performance and quality
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3, request_timeout=15)
    
    # Limit the number of products to process to avoid token limits
    max_products = 5  # Reduced from 8
    # Use slimmed products for GPT
    products_to_process = [slim_product(p) for p in products[:max_products]]
    
    # Create a more detailed product summary with all relevant fields
    product_strs = []
    for i, p in enumerate(products_to_process, 1):
        meta = p.get('metadata', {})
        
        # Handle new image structure - get all images
        image_urls = meta.get('image_urls', [])
        main_image_url = meta.get('main_image_url', '')
        
        # If no image_urls array, fall back to main_image_url
        if not image_urls and main_image_url:
            image_urls = [main_image_url]
        
        # Create image display string
        if image_urls:
            image_display = f"Images ({len(image_urls)} total):\n"
            for j, img_url in enumerate(image_urls[:5], 1):  # Show first 5 images
                image_display += f"   {j}. {img_url}\n"
            if len(image_urls) > 5:
                image_display += f"   ... and {len(image_urls) - 5} more images\n"
        else:
            image_display = "Images: No images available\n"
        
        product_strs.append(
            f"{i}. SKU: {meta.get('sku', 'N/A')}\n"
            f"   Category: {meta.get('category', 'N/A')}\n"
            f"   Color: {meta.get('color', 'N/A')}\n"
            f"   Material: {meta.get('material', 'N/A')}\n"
            f"   Features: {meta.get('characteristics_text', 'N/A')}\n"
            f"   Scene: {meta.get('scene', 'N/A')}\n"
            f"   {image_display}"
        )
    
    context = '\n'.join(product_strs)
    
    # Updated prompt to mention multiple images
    prompt = f"""Query: {user_query}

Products found: {len(products)}
Top results:
{context}

You're a helpful, confident, and witty product assistant. Be friendly, clever, and genuinely helpful.

Provide a conversational summary of what you found. Include:
1. Product SKUs
2. Brief, interesting, and useful descriptions
3. Image links: [Product Name](main_image_url) - mention if there are additional images available
4. Confident reasoning about why these are a great fit for the user's needs

Speak with confidence: "This would be a great fit for you because..."
Be creative and insightful—connect the product's features to the user's needs.
Avoid hedging or apologizing. Don't say "maybe," "possibly," or "if it's not what you want."
Be like a helpful friend who's excited to show you what they found—add some personality and reasoning!

Note: Each product may have multiple images available. Mention the main image and indicate if there are additional views available."""

    if language == "zh":
        prompt += " 用中文回答。"
    elif language and language != "en":
        prompt += f" Answer in {language}."
    
    response = llm.invoke(prompt)
    return response.content 