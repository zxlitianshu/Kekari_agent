from langchain_core.messages import HumanMessage
from langgraph_workflow.utils.helpers import generate_search_queries, pinecone_search, summarize_results, detect_language
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
            image_url = (metadata.get('main_image_url') or 
                        metadata.get('image_url') or 
                        metadata.get('image') or 
                        'N/A')
            print(f"   Product {i+1}: {image_url}")
    
    # 3. Summarize results
    summary_start = time.time()
    summary = summarize_results(user_query, all_matches, language=language)
    print(f"✅ RAG pipeline completed, returning summary... (summarization took {time.time() - summary_start:.2f}s)")
    print(f"⏱️ Total RAG time: {time.time() - start_time:.2f}s")
    
    # Update state with all info
    return {
        "messages": [HumanMessage(content=summary)],
        "user_query": user_query,
        "search_queries": search_queries,
        "search_results": all_matches,
        "final_summary": summary,
        "language": language
    } 