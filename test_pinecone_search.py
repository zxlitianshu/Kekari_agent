import openai
from pinecone import Pinecone
import config

openai.api_key = config.OPENAI_API_KEY

# 1. User query
user_query = "find me all tables that can be sold in a coffee shop"

# 2. Embed the query
response = openai.embeddings.create(
    input=user_query,
    model="text-embedding-3-small"
)
query_vector = response.data[0].embedding

# 3. Search Pinecone
pc = Pinecone(api_key=config.PINECONE_API_KEY)
index = pc.Index(config.INDEX_NAME)

# Query Pinecone for top 5 most similar vectors
results = index.query(
    vector=query_vector,
    top_k=5,
    include_metadata=True
)

# 4. Print image links for top 5
print("Top 5 product image URLs:")
for match in results['matches']:
    image_url = match['metadata'].get('main_image_url', 'No image URL')
    print(image_url) 