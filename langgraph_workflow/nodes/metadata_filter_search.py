from langchain_core.messages import HumanMessage
from langgraph_workflow.utils.helpers import generate_search_queries, pinecone_search

def metadata_filter_search_node(state):
    print("🔄 LangGraph: Executing 'metadata_filter_search' node...")
    user_query = state["user_query"]
    language = state.get("language", "en")
    filters = state.get("metadata_filters", {})
    print(f"📥 User query: {user_query} (language: {language}) with metadata filters: {filters}")
    # 1. Generate search queries
    search_queries = generate_search_queries(user_query)
    print(f"🔎 Generated search queries: {search_queries}")
    # 2. Run Pinecone search for each, with metadata filter
    all_matches = []
    seen_ids = set()
    for q in search_queries:
        matches = pinecone_search(q, filter=filters)
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
    print(f"📦 Retrieved {len(all_matches)} unique products (with metadata filter).")
    print("✅ Metadata filter RAG pipeline completed, returning search results...")
    # Update state with search results only - no verbose summary message
    return {
        **state,
        "search_queries": search_queries,
        "search_results": all_matches
    } 