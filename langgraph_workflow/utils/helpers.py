from langchain_community.chat_models import ChatOpenAI
import openai
import config
from langdetect import detect

# Helper: Use GPT to generate search queries from user query
def generate_search_queries(user_query, n=2):
    # Use GPT-4o for better performance
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1, request_timeout=10)
    prompt = f"""Query: '{user_query}'
Generate {n} short search terms (2-4 words each) for finding relevant products.
Return: ['term1', 'term2']"""

    response = llm.invoke(prompt)
    
    # Try to extract list from response
    try:
        # Look for list pattern in response
        import re
        list_match = re.search(r'\[.*?\]', response.content)
        if list_match:
            queries = eval(list_match.group())
            if isinstance(queries, list) and len(queries) > 0:
                return queries[:n]  # Limit to n queries
    except Exception:
        pass
    
    # Fallback: split by lines and clean up
    lines = [line.strip().strip('- ').strip('"').strip("'") for line in response.content.split('\n')]
    queries = [line for line in lines if line and len(line) > 2 and len(line) < 30]  # Reduced max length
    return queries[:n] if queries else [user_query]

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
    # Search Pinecone
    search_kwargs = dict(vector=query_vector, top_k=top_k, include_metadata=True)
    if filter:
        search_kwargs["filter"] = filter
    results = index.query(**search_kwargs)
    return results['matches']

# Helper: Detect language
def detect_language(text):
    try:
        return detect(text)
    except Exception:
        return "en"

# Helper: Summarize results with GPT
def summarize_results(user_query, products, language=None):
    # Use GPT-4o for better performance and quality
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3, request_timeout=15)
    
    # Limit the number of products to process to avoid token limits
    max_products = 5  # Reduced from 8
    products_to_process = products[:max_products]
    
    # Create a more detailed product summary with all relevant fields
    product_strs = []
    for i, p in enumerate(products_to_process, 1):
        meta = p.get('metadata', {})
        image_url = (meta.get('main_image_url') or 
                    meta.get('image_url') or 
                    meta.get('image') or 
                    'N/A')
        product_strs.append(
            f"{i}. SKU: {meta.get('sku', 'N/A')}\n"
            f"   Category: {meta.get('category', 'N/A')}\n"
            f"   Color: {meta.get('color', 'N/A')}\n"
            f"   Material: {meta.get('material', 'N/A')}\n"
            f"   Features: {meta.get('characteristics_text', 'N/A')}\n"
            f"   Scene: {meta.get('scene', 'N/A')}\n"
            f"   Image: {image_url}\n"
        )
    
    context = '\n'.join(product_strs)
    
    # Updated prompt remains the same
    prompt = f"""Query: {user_query}

Products found: {len(products)}
Top results:
{context}

You're a helpful, confident, and witty product assistant. Be friendly, clever, and genuinely helpful.

Provide a conversational summary of what you found. Include:
1. Product SKUs
2. Brief, interesting, and useful descriptions
3. Image links: [Product Name](image_url)
4. Confident reasoning about why these are a great fit for the user's needs

Speak with confidence: "This would be a great fit for you because..."
Be creative and insightful—connect the product's features to the user's needs.
Avoid hedging or apologizing. Don't say "maybe," "possibly," or "if it's not what you want."
Be like a helpful friend who's excited to show you what they found—add some personality and reasoning!"""

    if language == "zh":
        prompt += " 用中文回答。"
    elif language and language != "en":
        prompt += f" Answer in {language}."
    
    response = llm.invoke(prompt)
    return response.content 