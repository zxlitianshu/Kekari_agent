import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
from pinecone import Pinecone, ServerlessSpec
import openai
import config

print('OpenAI API Key:', config.OPENAI_API_KEY)

openai.api_key = config.OPENAI_API_KEY

# Determine region and input file
region = "US"
input_file = "all_new_skus_us.json"
if len(sys.argv) > 1 and sys.argv[1].lower() == "eu":
    region = "EU"
    input_file = "all_new_skus_eu.json"
print(f"Processing region: {region}, input file: {input_file}")

# 1. Load and parse your raw data (all products)
with open(input_file, "r") as f:
    all_products = json.load(f)

# 2. Clean and extract fields
def clean_html(raw_html):
    import re
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def parse_attributes(attr_str):
    import re
    color = material = scene = None
    if not attr_str:
        return color, material, scene
    if "main_color='" in attr_str:
        color = re.search(r"main_color='([^']*)'", attr_str)
        color = color.group(1) if color else None
    if "main_material='" in attr_str:
        material = re.search(r"main_material='([^']*)'", attr_str)
        material = material.group(1) if material else None
    if "scene=" in attr_str:
        scene = re.search(r"scene=([^,)]*)", attr_str)
        scene = scene.group(1) if scene else None
    return color, material, scene

def get_field(product, *names):
    for name in names:
        if name in product and product[name] is not None:
            return product[name]
    return None

# 3. Init Pinecone (new API)
pc = Pinecone(api_key=config.PINECONE_API_KEY)
index_name = config.INDEX_NAME

if not pc.has_index(index_name):
    pc.create_index(
        name=index_name,
        dimension=1536,  # or your embedding size
        metric="cosine",
        spec=ServerlessSpec(
            cloud=config.PINECONE_CLOUD,
            region=config.PINECONE_ENV
        )
    )
    print(f"Index '{index_name}' created.")
else:
    print(f"Index '{index_name}' already exists.")

index = pc.Index(index_name)

def get_text_embedding(text):
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# 4. Upsert all products
for product in all_products:
    product_id = product["sku"]
    title = product.get("name", "")
    description = clean_html(product.get("description", ""))
    characteristics = " ".join(product.get("characteristics", []) or [])
    text_for_embedding = f"{title}. {description}. {characteristics}"

    # Parse attributes string if needed
    color = material = scene = None
    attributes = product.get("attributes", "")
    if isinstance(attributes, str):
        color, material, scene = parse_attributes(attributes)
    elif isinstance(attributes, dict):
        color = attributes.get("main_color")
        material = attributes.get("main_material")
        scene = attributes.get("scene")

    # Only include selected fields as metadata, checking both snake_case and camelCase
    metadata = {}
    field_variants = [
        ("category",),
        ("category_code",),
        ("weight",),
        ("length",),
        ("width",),
        ("height",),
        ("weight_kg", "weightKg"),
        ("length_cm", "lengthCm"),
        ("width_cm", "widthCm"),
        ("height_cm", "heightCm"),
        ("sku",),
        ("main_image_url",),
        ("US",),
        ("EU",)
    ]
    for variants in field_variants:
        value = get_field(product, *variants)
        if value is not None:
            metadata[variants[0]] = value
    # Add parsed color/material/scene if present
    if color is not None:
        metadata["color"] = color
    if material is not None:
        metadata["material"] = material
    if scene is not None:
        metadata["scene"] = scene
    # Add characteristics as plain text
    characteristics_text = " ".join(product.get("characteristics", []) or [])
    metadata["characteristics_text"] = characteristics_text

    text_vector = get_text_embedding(text_for_embedding)
    index.upsert([
        (f"{product_id}_text", text_vector, {**metadata, "type": "text"})
    ])
    print(f"Upserted {product_id} to Pinecone.")

print("All products upserted to Pinecone.") 