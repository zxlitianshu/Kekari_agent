from langchain_core.messages import HumanMessage, AIMessage
import json
import time
from typing import Dict, List, Any
import requests
import sys
import os
from langchain_community.chat_models import ChatOpenAI

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import SHOP, ACCESS_TOKEN

def shopify_agent_node(state):
    """
    Publishes selected products to Shopify with LLM-generated titles and descriptions.
    """
    user_query = state.get("user_query", "")
    search_results = state.get("search_results", [])
    messages = state.get("messages", [])
    parsed_intent = state.get("parsed_intent", {})
    
    print("🔄 Shopify Agent: Starting product publishing process...")
    
    # Import listing database to get product details
    from .listing_database import ListingDatabase
    db = ListingDatabase()
    
    # ALWAYS check listing database first - this is the primary source
    listing_ready_skus = db.list_products()
    
    if listing_ready_skus:
        print(f"📋 Found {len(listing_ready_skus)} products in listing database - using these as primary source")
        
        # Get products from listing database
        listing_products = []
        for sku in listing_ready_skus:
            product_data = db.get_product(sku)
            if product_data:
                listing_products.append(product_data)
        
        if listing_products:
            print(f"✅ Using {len(listing_products)} products from listing database")
            # Use listing database products as primary source
            working_search_results = []
            for listing_product in listing_products:
                # Create a mock search result from listing database entry
                original_metadata = listing_product.get('original_metadata', {})
                # Update the main image to the modified image (if it exists)
                modified_image_url = listing_product.get('modified_image_url', '')
                if modified_image_url:
                    original_metadata['main_image_url'] = modified_image_url
                    # Add the modified image to the image_urls list at the beginning
                    image_urls = original_metadata.get('image_urls', [])
                    if modified_image_url not in image_urls:
                        image_urls.insert(0, modified_image_url)
                        original_metadata['image_urls'] = image_urls
                
                working_search_results.append({
                    'metadata': original_metadata,
                    'id': f"{listing_product.get('sku')}_listing",
                    'score': 1.0
                })
        else:
            print("⚠️ No valid products found in listing database, falling back to search results")
            working_search_results = search_results.copy() if search_results else []
    else:
        print("📋 No products in listing database, using search results as fallback")
        # Create a copy of search results to work with, don't modify the original
        working_search_results = search_results.copy() if search_results else []
    
    # Use parsed intent to determine which products to list
    if working_search_results and parsed_intent:
        selected_products = parsed_intent.get("selected_products", [])
        selected_skus = parsed_intent.get("selected_skus", [])
        reasoning = parsed_intent.get("reasoning", "")
        confidence = parsed_intent.get("confidence", 0.0)
        language = parsed_intent.get("language", "en")
        
        print(f"🔍 Intent Parser Results: {reasoning}")
        print(f"🎯 Selected SKUs: {selected_skus}")
        print(f"📊 Confidence: {confidence}")
        print(f"🌐 Language: {language}")
        
        # Filter products based on intent parser results
        if selected_skus:
            filtered_results = []
            for product in working_search_results:
                sku = product.get('metadata', {}).get('sku', '')
                if sku in selected_skus:
                    filtered_results.append(product)
            
            if filtered_results:
                working_search_results = filtered_results
                print(f"✅ Filtered to {len(filtered_results)} products: {selected_skus}")
            else:
                print(f"⚠️ No matching products found for SKUs: {selected_skus}")
        else:
            print("🔍 No specific SKUs identified, using all available products")
    else:
        print("🔍 No intent parser results available, using all available products")
        language = "en"
    
    if not working_search_results:
        return {
            "messages": [HumanMessage(content="❌ No products found to publish to Shopify.")],
            **state
        }
    print(f"🔍 Found {len(working_search_results)} products to process for Shopify\n")

    # Deduplicate by SKU
    unique_products = {}
    for match in working_search_results:
        metadata = match.get('metadata', {})
        sku = metadata.get('sku')
        if sku and sku not in unique_products:
            unique_products[sku] = match
    print(f"📦 Deduplicated to {len(unique_products)} unique products by SKU\n")

    successful_products = []
    failed_products = []
    product_links = []
    for idx, (sku, match) in enumerate(unique_products.items(), 1):
        metadata = match.get('metadata', {})
        print(f"🔄 Processing product {idx}/{len(unique_products)}: {sku}")
        try:
            # NEW: Generate AI-written title and description
            llm = ChatOpenAI(model="gpt-4o", temperature=0.7, request_timeout=15)
            
            # Prepare product data for LLM
            product_data = f"""
SKU: {metadata.get('sku', 'N/A')}
Category: {metadata.get('category', 'N/A')}
Material: {metadata.get('material', 'N/A')}
Color: {metadata.get('color', 'N/A')}
Features: {metadata.get('characteristics_text', 'N/A')}
Dimensions: Height: {metadata.get('height', 'N/A')}", Width: {metadata.get('width', 'N/A')}", Length: {metadata.get('length', 'N/A')}"
Weight: {metadata.get('weight', 'N/A')} lbs
Scene: {metadata.get('scene', 'N/A')}
"""
            
            # Generate title
            title_prompt = f"""
Create a compelling, SEO-friendly product title for this item. Make it attractive and descriptive.

Product Information:
{product_data}

Requirements:
- Keep it under 100 characters
- Include key features like material, color, or type
- Make it appealing to customers
- Don't include SKU in the title
- Be specific and descriptive

Title:"""
            
            title_response = llm.invoke(title_prompt)
            ai_title = title_response.content.strip().strip('"').strip("'")
            
            # Generate description
            desc_prompt = f"""
Create a compelling product description for this item. Make it engaging and informative.

Product Information:
{product_data}

Requirements:
- Write 2-3 paragraphs
- Highlight key features and benefits
- Make it appealing to customers
- Include practical use cases
- Be enthusiastic but professional
- Don't include SKU in the description

Description:"""
            
            desc_response = llm.invoke(desc_prompt)
            ai_description = desc_response.content.strip()
            
            print(f"🤖 Generated AI Title: {ai_title}")
            print(f"🤖 Generated AI Description: {ai_description[:100]}...")
            
            # Create product input with AI-generated content
            product_input = create_product_input_from_metadata(metadata, ai_title, ai_description)
            # NEW: Pass modified_images to create_media_from_metadata
            media = create_media_from_metadata(metadata, [])
            result = publish_product_to_shopify(product_input, media, metadata)
            if result.get('success'):
                successful_products.append(result)
                print(f"✅ Successfully published: {result.get('title', sku)}\n")
                # After publishing each product, collect the Shopify product link and title
                shopify_url = result.get('live_url') or result.get('shopify_url') or result.get('url')
                title = result.get('title', ai_title)
                if shopify_url:
                    product_links.append({'title': title, 'url': shopify_url})
                    print(f"🔗 Added product link: {title} -> {shopify_url}")
                else:
                    print(f"⚠️ No URL found for published product: {title}")
            else:
                failed_products.append({"sku": sku, "error": result.get('error', 'Unknown error')})
                print(f"❌ Failed to publish: {sku} - {result.get('error', 'Unknown error')}\n")
        except Exception as e:
            failed_products.append({"sku": sku, "error": str(e)})
            print(f"❌ Exception for {sku}: {e}\n")

    # After all products processed, generate a friendly LLM message if at least one was successful
    print(f"🔍 Debug - product_links count: {len(product_links)}")
    print(f"🔍 Debug - product_links content: {product_links}")
    if product_links:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.3, request_timeout=10)
        links_str = "\n".join([f"- {p['title']}: {p['url']}" for p in product_links])
        
        # Generate language-appropriate prompt
        if language == "zh" or language == "zh-cn":
            prompt = f"""
你刚刚帮助用户将产品上架到Shopify。以下是产品标题和链接：
{links_str}
用中文写一个友好的祝贺消息给用户，列出每个产品及其标题和链接。要简洁且热情。
"""
        else:
            prompt = f"""
You just helped a user list products on Shopify. Here are the product titles and their links:
{links_str}
Write a friendly, congratulatory message to the user, listing each product with its title and link. Be concise and enthusiastic.
"""
        
        llm_message = llm.invoke(prompt).content
        state = dict(state)
        state["messages"] = state.get("messages", []) + [AIMessage(content=llm_message)]
        # CRITICAL: Don't modify search_results in the returned state
        # Keep the original search_results so they don't get overwritten in global state
        print("🔍 Shopify Agent - Final messages list:")
        for i, m in enumerate(state["messages"]):
            print(f"{i}: {getattr(m, 'content', m)} (type: {getattr(m, 'type', None)}, role: {getattr(m, 'role', None)})")
        return state
    
    # If no products were successfully published, return failure message
    if language == "zh" or language == "zh-cn":
        success_message = "❌ 没有产品成功上架到Shopify。"
    else:
        success_message = "❌ No products were successfully published to Shopify."
    
    state = dict(state)
    state["messages"] = state.get("messages", []) + [AIMessage(content=success_message)]
    # CRITICAL: Don't modify search_results in the returned state
    print("🔍 Shopify Agent - Final messages list:")
    for i, m in enumerate(state["messages"]):
        print(f"{i}: {getattr(m, 'content', m)} (type: {getattr(m, 'type', None)}, role: {getattr(m, 'role', None)})")
    return state

def create_product_input_from_metadata(metadata: Dict[str, Any], ai_title: str, ai_description: str) -> Dict[str, Any]:
    """Create Shopify product input from vector search metadata"""
    
    # Use AI-generated title and description
    title = ai_title if ai_title else "Product"
    description = ai_description if ai_description else ""
    
    # Create HTML description with AI-generated content
    description_html = create_description_html(metadata, ai_description)
    
    return {
        "title": title,
        "descriptionHtml": description_html,
        "productType": metadata.get('category', 'General'),
        "vendor": metadata.get('vendor', 'Default Vendor'),
        "status": "ACTIVE"
    }

    # Add category if available
    category = metadata.get('category', '')
    if category:
        title_parts.append(category)
    
    # Add material if available
    material = metadata.get('material', '')
    if material:
        title_parts.append(material)
    
    # Add color if available
    color = metadata.get('color', '')
    if color:
        title_parts.append(color)
    
    # Add SKU if available
    sku = metadata.get('sku', '')
    if sku:
        title_parts.append(f"({sku})")
    
    # Create title
    if title_parts:
        title = " ".join(title_parts)
    else:
        title = f"Product {sku}" if sku else "Product"
    
    # Create description from characteristics_text if available
    description = metadata.get('characteristics_text', metadata.get('description', ''))
    
    # Create HTML description if we have structured data
    description_html = create_description_html(metadata)
    
    return {
        "title": title,
        "descriptionHtml": description_html,
        "productType": metadata.get('category', 'General'),
        "vendor": metadata.get('vendor', 'Default Vendor'),
        "status": "ACTIVE"
    }

def create_description_html(metadata: Dict[str, Any], ai_description: str = "") -> str:
    """Create rich HTML description from metadata"""
    
    # Start with basic description
    html_parts = []
    
    # Get all images from the new structure
    image_urls = metadata.get('image_urls', [])
    main_image_url = metadata.get('main_image_url', '')
    
    # If we have multiple images, create an image gallery
    if image_urls and len(image_urls) > 1:
        html_parts.append('<div style="width:100%; margin-top:24px;">')
        html_parts.append('<div style="font-size: 16px; font-weight:bold;line-height:24px;color: #333333;word-break: break-word;">Product Images:</div>')
        
        # Show first image as main
        if main_image_url and main_image_url in image_urls:
            html_parts.append(f'<div><img src="{main_image_url}" alt="Main Product Image" style="width: 100%;display:block; margin-top:12px;"></div>')
        
        # Show additional images in a grid
        if len(image_urls) > 1:
            html_parts.append('<div style="display:flex; flex-wrap:wrap; gap:12px; margin-top:12px;">')
            for i, img_url in enumerate(image_urls[:6], 1):  # Show up to 6 additional images
                if img_url != main_image_url:  # Don't duplicate main image
                    html_parts.append(f'''
                    <div style="flex: 1; min-width: 200px; max-width: 300px;">
                        <img src="{img_url}" alt="Product View {i}" style="width: 100%; height: auto; border-radius: 8px;">
                    </div>
                    ''')
            html_parts.append('</div>')
            
            if len(image_urls) > 7:
                html_parts.append(f'<p style="margin-top:12px; color: #666; font-size: 14px;">+ {len(image_urls) - 7} additional product views available</p>')
        
        html_parts.append('</div>')
    
    # Fallback to single main image
    elif main_image_url:
        html_parts.append(f'<div><img src="{main_image_url}" alt="Product Image" style="width: 100%;display:block; margin-top:24px;"></div>')
    
    # Add AI-generated description first
    if ai_description:
        html_parts.append(f'''
        <div style="width:100%; margin-top:24px;">
        <div style="font-size: 16px; font-weight:bold;line-height:24px;color: #333333;word-break: break-word;">Product Description:</div>
        <div style="margin-top:12px;word-break: break-word;white-space:pre-line;line-height:18px;">{ai_description}</div>
        </div>
        ''')
    
    # Add original characteristics_text as additional details if different from AI description
    original_description = metadata.get('characteristics_text', metadata.get('description', ''))
    if original_description and original_description != ai_description:
        html_parts.append(f'''
        <div style="width:100%; margin-top:24px;">
        <div style="font-size: 16px; font-weight:bold;line-height:24px;color: #333333;word-break: break-word;">Product Specifications:</div>
        <div style="margin-top:12px;word-break: break-word;white-space:pre-line;line-height:18px;">{original_description}</div>
        </div>
        ''')
    
    # Add specifications table if we have structured data
    specs = extract_specifications(metadata)
    if specs:
        html_parts.append(create_specifications_table(specs))
    
    return '\n'.join(html_parts)

def extract_specifications(metadata: Dict[str, Any]) -> Dict[str, str]:
    """Extract product specifications from metadata"""
    specs = {}
    
    # Map common fields to specification names
    spec_mapping = {
        'weight': 'Weight',
        'weight_kg': 'Weight (kg)',
        'length': 'Length',
        'width': 'Width', 
        'height': 'Height',
        'length_cm': 'Length (cm)',
        'width_cm': 'Width (cm)',
        'height_cm': 'Height (cm)',
        'material': 'Material',
        'category': 'Category',
        'scene': 'Scene',
        'US': 'US Market',
        'EU': 'EU Market'
    }
    
    for key, display_name in spec_mapping.items():
        if key in metadata and metadata[key]:
            specs[display_name] = str(metadata[key])
    
    return specs

def create_specifications_table(specs: Dict[str, str]) -> str:
    """Create HTML table for specifications"""
    if not specs:
        return ""
    
    rows = []
    for key, value in specs.items():
        rows.append(f'''
        <tr>
        <td style="width: 40%;line-height:24px;padding: 12px 16px;background: #F7F8FA;border-right: 1px solid #E5E5E5;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">{key}</td>
        <td style="width: 60%;line-height:18px;padding: 12px 16px;border-bottom: 1px solid #E5E5E5;word-break: break-word;white-space: pre-wrap">{value}</td>
        </tr>
        ''')
    
    return f'''
    <div style="width:100%; margin-top:24px;">
    <div style="font-size: 16px; font-weight:bold;line-height:24px;color: #333333;">Product Specifications</div>
    <table style="width:100%; margin-top:12px;border: 1px solid #E5E5E5;border-bottom:0;" cellspacing="0">
    <tbody>
    {''.join(rows)}
    </tbody>
    </table>
    </div>
    '''

def create_media_from_metadata(metadata: Dict[str, Any], modified_images: List[Dict] = None) -> List[Dict[str, str]]:
    """Create media array from metadata, including modified images if available"""
    media = []
    
    # Get all images from the new structure
    image_urls = metadata.get('image_urls', [])
    main_image_url = metadata.get('main_image_url', '')
    sku = metadata.get('sku', '')
    
    # NEW: Check if we have modified images for this SKU
    modified_image_url = None
    if modified_images:
        for img_result in modified_images:
            if img_result.get('sku') == sku and img_result.get('status') == 'success':
                modified_image_url = img_result.get('modified_image_url')
                break
    
    # If we have a modified image, use it as the main image
    if modified_image_url:
        media.append({
            "originalSource": modified_image_url,
            "mediaContentType": "IMAGE"
        })
        print(f"🎨 Shopify Agent: Using modified image for SKU {sku}: {modified_image_url}")
    
    # Add original images (but skip the main one if we're using a modified version)
    if image_urls:
        for img_url in image_urls:
            if img_url and img_url.strip():
                # Skip the main image if we're using a modified version
                if modified_image_url and img_url.strip() == main_image_url:
                    continue
                media.append({
                    "originalSource": img_url.strip(),
                    "mediaContentType": "IMAGE"
                })
    # Fallback to main_image_url if image_urls is not available and no modified image
    elif main_image_url and not modified_image_url:
        media.append({
            "originalSource": main_image_url,
            "mediaContentType": "IMAGE"
        })
    
    # Remove duplicates while preserving order
    seen_urls = set()
    unique_media = []
    for item in media:
        if item["originalSource"] not in seen_urls:
            unique_media.append(item)
            seen_urls.add(item["originalSource"])
    
    return unique_media

def publish_product_to_shopify(product_input: Dict[str, Any], media: List[Dict[str, str]], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use the existing shopify_listing.py logic to publish a product
    Returns: {'success': bool, 'title': str, 'live_url': str, 'product_id': str, 'error': str}
    """
    try:
        url = f"https://{SHOP}/admin/api/2025-04/graphql.json"
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": ACCESS_TOKEN
        }
        
        # Step 1: Get Online Store publication ID
        publications_query = """
        query {
          publications(first: 10) {
            edges {
              node {
                id
                name
              }
            }
          }
        }
        """
        
        resp = requests.post(url, headers=headers, json={"query": publications_query})
        result = resp.json()
        
        # Find the Online Store publication
        publication_id = None
        for edge in result["data"]["publications"]["edges"]:
            if "Online Store" in edge["node"]["name"]:
                publication_id = edge["node"]["id"]
                break
        
        if not publication_id:
            raise Exception("Online Store publication ID not found!")
        
        # Step 2: Create Product
        create_product_query = """
        mutation productCreate($input: ProductInput!, $media: [CreateMediaInput!]) {
          productCreate(input: $input, media: $media) {
            product { id title }
            userErrors { field message }
          }
        }
        """
        variables = {"input": product_input, "media": media}
        resp = requests.post(url, headers=headers, json={"query": create_product_query, "variables": variables})
        result = resp.json()
        
        if result.get("errors"):
            raise Exception(f"Product creation error: {result['errors']}")
        
        if result["data"]["productCreate"]["userErrors"]:
            raise Exception(f"Product creation user errors: {result['data']['productCreate']['userErrors']}")
        
        product_id = result["data"]["productCreate"]["product"]["id"]
        
        # Step 3: Publish the product
        publish_mutation = """
        mutation publishProduct($id: ID!, $input: [PublicationInput!]!) {
          publishablePublish(id: $id, input: $input) {
            publishable {
              ... on Product {
                id
                title
                status
                publishedAt
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        
        publish_variables = {
            "id": product_id,
            "input": [{"publicationId": publication_id}]
        }
        
        publish_response = requests.post(url, headers=headers, json={"query": publish_mutation, "variables": publish_variables}).json()
        
        if publish_response.get("errors"):
            raise Exception(f"Publish error: {publish_response['errors']}")
        
        publish_data = publish_response.get("data", {}).get("publishablePublish", {})
        if publish_data.get("userErrors"):
            raise Exception(f"Publish user errors: {publish_data['userErrors']}")
        
        # Step 4: Get default location ID
        locations_query = """
        query {
          locations(first: 10) {
            edges {
              node {
                id
                name
              }
            }
          }
        }
        """
        
        locations_response = requests.post(url, headers=headers, json={"query": locations_query}).json()
        if locations_response.get("errors"):
            raise Exception(f"Location error: {locations_response['errors']}")
        
        locations_data = locations_response.get("data", {}).get("locations", {}).get("edges", [])
        if not locations_data:
            raise Exception("No locations found")
        
        location_id = locations_data[0]["node"]["id"]
        
        # Step 5: Update variant with SKU, price, and inventory
        sku = metadata.get('sku', 'DEFAULT-SKU')
        price = metadata.get('price', '100.00')
        
        update_variant_mutation = """
        mutation productVariantsBulkCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!, $strategy: ProductVariantsBulkCreateStrategy!) {
          productVariantsBulkCreate(productId: $productId, variants: $variants, strategy: $strategy) {
            productVariants {
              id
              sku
              price
              title
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        
        update_variant_variables = {
            "productId": product_id,
            "variants": [
                {
                    "price": str(price),
                    "inventoryItem": {"sku": sku},
                    "inventoryQuantities": [
                        {
                            "availableQuantity": 100,
                            "locationId": location_id
                        }
                    ]
                }
            ],
            "strategy": "REMOVE_STANDALONE_VARIANT"
        }
        
        update_variant_response = requests.post(url, headers=headers, json={"query": update_variant_mutation, "variables": update_variant_variables}).json()
        
        if update_variant_response.get("errors"):
            raise Exception(f"Variant update error: {update_variant_response['errors']}")
        
        update_variant_data = update_variant_response.get("data", {}).get("productVariantsBulkCreate", {})
        if update_variant_data.get("userErrors"):
            raise Exception(f"Variant update user errors: {update_variant_data['userErrors']}")
        
        # Step 6: Get the live product URL
        get_product_query = """
        query getProduct($id: ID!) {
          product(id: $id) {
            id
            title
            handle
            onlineStoreUrl
          }
        }
        """
        
        product_response = requests.post(url, headers=headers, json={"query": get_product_query, "variables": {"id": product_id}}).json()
        if product_response.get("errors"):
            raise Exception(f"Product URL error: {product_response['errors']}")
        
        product_data = product_response.get("data", {}).get("product", {})
        handle = product_data.get("handle")
        online_store_url = product_data.get("onlineStoreUrl")
        
        if online_store_url:
            live_url = online_store_url
        else:
            live_url = f"https://{SHOP}/products/{handle}"
        
        return {
            'success': True,
            'title': product_input['title'],
            'live_url': live_url,
            'product_id': product_id,
            'sku': sku,
            'price': price,
            'admin_url': f"https://{SHOP}/admin/products/{product_id.split('/')[-1]}"
        }
        
    except Exception as e:
        return {
            'success': False,
            'title': product_input.get('title', 'Unknown'),
            'error': str(e)
        }

def generate_shopify_response(successful_products: List[Dict], failed_products: List[Dict], total_count: int) -> str:
    """Generate a conversational, friendly response about the Shopify publishing results using LLM"""
    
    if not successful_products and not failed_products:
        return "❌ No products were processed for Shopify publishing."
    
    # Prepare product details for LLM
    product_details = []
    for i, product in enumerate(successful_products, 1):
        if 'shopify_result' in product:
            result = product['shopify_result']
        else:
            result = product
            
        product_details.append({
            "title": result.get('title', 'Unknown Product'),
            "sku": result.get('sku', 'N/A'),
            "price": result.get('price', 'N/A'),
            "live_url": result.get('live_url', 'N/A'),
            "admin_url": result.get('admin_url', 'N/A')
        })
    
    # Prepare error details
    error_details = []
    for product in failed_products:
        original_product = product['product']
        error = product['error']
        sku = original_product.get('metadata', {}).get('sku', 'Unknown SKU')
        name = original_product.get('metadata', {}).get('name', 'Unknown Product')
        error_details.append({
            "name": name,
            "sku": sku,
            "error": error
        })
    
    # Use LLM to generate friendly response
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7, request_timeout=15)
    
    prompt = f"""
You are a helpful e-commerce assistant. The user just listed some products on Shopify. Generate a friendly, conversational response that:

1. Confirms the products were successfully listed
2. Presents the live product URLs in a natural, clickable way
3. Asks if they want to make any changes or need help with anything else
4. Be enthusiastic and helpful

Here are the successfully listed products:
{json.dumps(product_details, indent=2)}

Here are any failed products (if any):
{json.dumps(error_details, indent=2)}

Total products processed: {total_count}
Successfully listed: {len(successful_products)}
Failed: {len(failed_products)}

Generate a friendly, conversational response. Make the URLs clickable by formatting them as markdown links. Be enthusiastic about their success and offer to help with anything else they might need.
"""
    
    try:
        response = llm.invoke(prompt)
        final_response = response.content
        
        # Debug: Print the response being generated
        print("🔍 Debug - LLM Generated Shopify Response:")
        print(final_response)
        print("🔍 Debug - Response length:", len(final_response))
        
        return final_response
        
    except Exception as e:
        # Fallback to original format if LLM fails
        print(f"🔍 Debug - LLM failed, using fallback response: {e}")
        
        response_parts = []
        response_parts.append(f"🎉 **Shopify Publishing Results**")
        response_parts.append(f"📊 **Summary:** {len(successful_products)}/{total_count} products successfully published")
        
        if successful_products:
            response_parts.append(f"\n✅ **Successfully Published Products:**")
            for i, product in enumerate(successful_products, 1):
                if 'shopify_result' in product:
                    result = product['shopify_result']
                else:
                    result = product
                    
                response_parts.append(f"\n{i}. **{result['title']}**")
                response_parts.append(f"   • SKU: {result.get('sku', 'N/A')}")
                response_parts.append(f"   • Price: ${result.get('price', 'N/A')}")
                response_parts.append(f"   • Live URL: {result.get('live_url', 'N/A')}")
                response_parts.append(f"   • Admin URL: {result.get('admin_url', 'N/A')}")
        
        if failed_products:
            response_parts.append(f"\n❌ **Failed Products:**")
            for i, product in enumerate(failed_products, 1):
                original_product = product['product']
                error = product['error']
                sku = original_product.get('metadata', {}).get('sku', 'Unknown SKU')
                name = original_product.get('metadata', {}).get('name', 'Unknown Product')
                response_parts.append(f"\n{i}. **{name}** (SKU: {sku})")
                response_parts.append(f"   • Error: {error}")
        
        return '\n'.join(response_parts)
