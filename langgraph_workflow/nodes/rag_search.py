from langchain_core.messages import HumanMessage
from langgraph_workflow.utils.helpers import generate_search_queries, pinecone_search, detect_language
import time

def rag_search_node(state):
    start_time = time.time()
    print("🔄 LangGraph: Executing 'rag_search' node...")
    
    user_query = state["messages"][-1].content
    language = detect_language(user_query)
    print(f"📥 User query: {user_query} (language: {language})")
    
    # 1. Generate search queries
    query_start = time.time()
    search_queries = generate_search_queries(user_query)
    print(f"🔎 Generated search queries: {search_queries} (took {time.time() - query_start:.2f}s)")
    
    # 2. Run Pinecone search for each
    search_start = time.time()
    all_matches = []
    seen_ids = set()
    for q in search_queries:
        matches = pinecone_search(q)
        for m in matches:
            if m['id'] not in seen_ids:
                # Only keep serializable fields
                all_matches.append({
                    'id': m.get('id'),
                    'score': m.get('score'),
                    'metadata': m.get('metadata'),
                    'values': m.get('values'),
                })
                seen_ids.add(m['id'])
    print(f"📦 Retrieved {len(all_matches)} unique products. (took {time.time() - search_start:.2f}s)")
    
    # Debug: Show image URLs found
    if all_matches:
        print("🔍 Debug - Image URLs found:")
        for i, match in enumerate(all_matches[:3]):  # Show first 3
            metadata = match.get('metadata', {})
            image_urls = metadata.get('image_urls', [])
            main_image_url = metadata.get('main_image_url', '')
            total_images = metadata.get('total_images', 0)
            
            if image_urls:
                print(f"   Product {i+1}: {len(image_urls)} images available")
                print(f"      Main: {main_image_url}")
                if len(image_urls) > 1:
                    print(f"      Additional: {len(image_urls) - 1} more images")
            elif main_image_url:
                print(f"   Product {i+1}: 1 image - {main_image_url}")
            else:
                print(f"   Product {i+1}: No images available")
    
    print(f"✅ RAG pipeline completed, returning search results... (took {time.time() - start_time:.2f}s)")
    
    # Update state with search results
    return {
        "user_query": user_query,
        "search_queries": search_queries,
        "search_results": all_matches,
        "language": language
    } 