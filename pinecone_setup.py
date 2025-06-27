from pinecone import Pinecone, ServerlessSpec
import config

pc = Pinecone(api_key=config.PINECONE_API_KEY)
index_name = config.INDEX_NAME

if not pc.has_index(index_name):
    pc.create_index_for_model(
        name=index_name,
        cloud=config.PINECONE_CLOUD,
        region=config.PINECONE_ENV,
        embed={
            "model": "llama-text-embed-v2",
            "field_map": {"text": "chunk_text"}
        }
    )
    print(f"Index '{index_name}' created.")
else:
    print(f"Index '{index_name}' already exists.") 