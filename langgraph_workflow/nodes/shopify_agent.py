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

# Import functions from listing_database
from .listing_database import validate_image_resolution, compress_image_url

def select_products_with_llm(messages: List, search_results: List, user_query: str) -> List:
    """
    Use LLM to determine which products to list based on conversation context and user query.
    """
    if not search_results:
        return []
    
    # Check if there are any recently modified products in the conversation
    modified_products = []
    for msg in messages[-5:]:  # Check last 5 messages for image modifications
        if hasattr(msg, 'content'):
            content = msg.content
            if isinstance(content, str) and any(keyword in content.lower() for keyword in ['modified', 'changed', 'updated', 'processed', 'successfully']):
                # Look for actual product SKUs in the message (not random URL strings)
                import re
                # Look for SKU patterns like W2640P257528, GS008004AAA, etc.
                sku_pattern = r'\b[A-Z]{2}\d+[A-Z]*\b'
                sku_matches = re.findall(sku_pattern, content)
                # Filter out obvious non-SKUs (like URL fragments)
                valid_skus = [sku for sku in sku_matches if len(sku) >= 8 and any(char.isdigit() for char in sku)]
                modified_products.extend(valid_skus)
    
    # Use LLM-based selection for all cases - no hardcoded keyword matching
    try:
        # Build conversation context
        conversation_parts = []
        for msg in messages[-5:]:  # Only use last 5 messages to avoid old irrelevant context
            if hasattr(msg, 'content'):
                content = msg.content
                if isinstance(content, list):
                    # Handle multimodal content
                    text_parts = []
                    for item in content:
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                    content = " ".join(text_parts)
                # Only include messages that are relevant to product selection
                if content.strip() and not content.startswith("✅") and not content.startswith("🔄"):
                    conversation_parts.append(f"{'User' if hasattr(msg, 'type') and msg.type == 'human' else 'Assistant'}: {content}")
        
        conversation_context = "\n".join(conversation_parts)
        
        # Build product list with descriptive names
        product_list = []
        for i, product in enumerate(search_results, 1):
            metadata = product.get('metadata', {})
            sku = metadata.get('sku', '')
            
            # Create descriptive name from available fields
            name_parts = []
            if metadata.get('category'):
                name_parts.append(metadata.get('category'))
            if metadata.get('material'):
                name_parts.append(metadata.get('material'))
            if metadata.get('color'):
                name_parts.append(metadata.get('color'))
            if metadata.get('characteristics_text'):
                name_parts.append(metadata.get('characteristics_text'))
            
            descriptive_name = " ".join(name_parts) if name_parts else f"Product {i}"
            
            product_info = f"{i}. SKU: {sku}, Name: {descriptive_name}"
            if metadata.get('scene'):
                product_info += f", Scene: {metadata.get('scene')}"
            
            # Mark recently modified products
            if sku in modified_products:
                product_info += " [RECENTLY MODIFIED]"
            
            product_list.append(product_info)
        
        product_list_text = "\n".join(product_list)
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        
        prompt = f"""You are an expert at understanding user intent for product selection in e-commerce workflows. Your task is to analyze the user's natural language request and determine which specific products they want to list on Shopify.

CONVERSATION CONTEXT:
{conversation_context}

AVAILABLE PRODUCTS:
{product_list_text}

RECENTLY MODIFIED PRODUCTS: {modified_products}

USER'S CURRENT QUERY:
{user_query}

TASK: Understand the user's intent and select the appropriate products for Shopify listing.

ANALYSIS APPROACH:
1. **Understand the user's intent**: What are they trying to accomplish?
2. **Identify product references**: How are they referring to specific products?
3. **Consider context**: What products have been discussed or modified recently?
4. **Match characteristics**: What product attributes are they mentioning?

INTENT UNDERSTANDING:
- **Specific product request**: User mentions particular characteristics, SKU, or refers to a specific product
- **Recent product reference**: User refers to recently discussed or modified products
- **General category request**: User wants all products of a certain type
- **All products request**: User explicitly wants everything

PRODUCT REFERENCE PATTERNS:
- **Direct SKU mention**: "W2103P277202", "SKU W1880115228"
- **Characteristic matching**: "black chair", "yellow linen", "white plastic"
- **Positional reference**: "the first one", "this product", "that chair"
- **Contextual reference**: "the one we just modified", "the chair I liked"
- **Category reference**: "all chairs", "every table", "chairs only"

SELECTION LOGIC:
1. **Exact SKU match**: If user mentions a specific SKU, select only that product
2. **Characteristic match**: If user mentions specific attributes, find products matching ALL mentioned characteristics
3. **Recent context**: If user refers to recently discussed/modified products, prioritize those
4. **Category match**: If user mentions a product type, select all products of that type
5. **Default behavior**: Only select all products if user explicitly requests everything

EXAMPLES OF USER INTENTS:
- "list only Patio Rocking Chair - White SKU: W2103P277202" → Select W2103P277202 only
- "list the black hdpe chair" → Select black HDPE chairs only
- "list this product" → Select most recently modified product
- "list all chairs" → Select all chair products
- "上架黑椅子" → Select black chairs only
- "publish the yellow one" → Select yellow products only
- "list everything" → Select all products

Return a JSON response with:
{{
    "selected_skus": ["SKU1", "SKU2", ...],
    "reasoning": "Detailed explanation of how you interpreted the user's intent and why these specific products were selected",
    "confidence": 0.95
}}

If you cannot determine specific products, return an empty array for selected_skus and explain why.

Response:"""

        response = llm.invoke(prompt)
        response_content = response.content.strip()
        
        # Better JSON parsing with fallback - handle markdown-wrapped JSON
        try:
            # Remove markdown code blocks if present
            if response_content.startswith('```'):
                # Extract content between code blocks
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_content, re.DOTALL)
                if json_match:
                    response_content = json_match.group(1)
                else:
                    # Try to find JSON object in the response
                    json_match = re.search(r'\{.*?\}', response_content, re.DOTALL)
                    if json_match:
                        response_content = json_match.group(0)
            
            result = json.loads(response_content)
        except json.JSONDecodeError:
            print(f"❌ JSON parsing failed, response was: {response_content}")
            # Try to extract SKUs from the response text
            import re
            sku_matches = re.findall(r'\b[A-Z]{2}\d+[A-Z]*\b', response_content)
            valid_skus = [sku for sku in sku_matches if len(sku) >= 8 and any(char.isdigit() for char in sku)]
            if valid_skus:
                result = {"selected_skus": valid_skus, "reasoning": "Extracted from text response", "confidence": 0.5}
            else:
                result = {"selected_skus": [], "reasoning": "JSON parsing failed", "confidence": 0.0}
        
        selected_skus = result.get("selected_skus", [])
        reasoning = result.get("reasoning", "")
        confidence = result.get("confidence", 0.0)
        
        print(f"🤖 LLM Product Selection:")
        print(f"   Reasoning: {reasoning}")
        print(f"   Selected SKUs: {selected_skus}")
        print(f"   Confidence: {confidence}")
        print(f"   Recently Modified Products: {modified_products}")
        
        if selected_skus:
            # Filter products based on selected SKUs
            filtered_products = []
            for product in search_results:
                sku = product.get('metadata', {}).get('sku', '')
                if sku in selected_skus:
                    filtered_products.append(product)
            
            if filtered_products:
                return filtered_products
            else:
                print(f"⚠️ No matching products found for selected SKUs: {selected_skus}")
                # If no matches but we have recently modified products, use those
                if modified_products:
                    print(f"🔄 Falling back to recently modified products: {modified_products}")
                    modified_filtered = []
                    for product in search_results:
                        sku = product.get('metadata', {}).get('sku', '')
                        if sku in modified_products:
                            modified_filtered.append(product)
                    if modified_filtered:
                        return modified_filtered
                return search_results  # Final fallback to all products
        else:
            print("🔍 No specific products selected")
            # If no specific selection but we have recently modified products, use those
            if modified_products:
                print(f"🔄 Using recently modified products: {modified_products}")
                modified_filtered = []
                for product in search_results:
                    sku = product.get('metadata', {}).get('sku', '')
                    if sku in modified_products:
                        modified_filtered.append(product)
                if modified_filtered:
                    return modified_filtered
            print("🔍 Using all available products")
            return search_results  # Use all products if no specific selection
            
    except Exception as e:
        print(f"❌ Error in LLM product selection: {e}")
        # Fallback to recently modified products if available
        if modified_products:
            print(f"🔄 Error fallback to recently modified products: {modified_products}")
            modified_filtered = []
            for product in search_results:
                sku = product.get('metadata', {}).get('sku', '')
                if sku in modified_products:
                    modified_filtered.append(product)
            if modified_filtered:
                return modified_filtered
        return search_results  # Final fallback to all products

def shopify_agent_node(state):
    """
    Publishes selected products to Shopify with LLM-generated titles and descriptions.
    Uses unified ProductSelectionIntentParser for product selection.
    """
    user_query = state.get("user_query", "")
    search_results = state.get("search_results", [])
    messages = state.get("messages", [])
    
    # Detect language
    is_chinese = any('\u4e00' <= char <= '\u9fff' for char in user_query)
    language = "zh" if is_chinese else "en"
    
    print("🔄 Shopify Agent: Starting product publishing process...")
    
    # Import listing database to get product details
    from .listing_database import ListingDatabase
    db = ListingDatabase()
    
    # Get products from listing database (primary source)
    listing_ready_skus = db.list_products()
    
    if not listing_ready_skus:
        print("❌ No products found in listing database")
        return {
            **state,
            "shopify_status": {"success": False, "message": "No products found in listing database. Please search for products first."}
        }
    
    print(f"📋 Found {len(listing_ready_skus)} products in listing database")
    
    # Get products from listing database
    listing_products = []
    for sku in listing_ready_skus:
        product_data = db.get_product(sku)
        if product_data:
            listing_products.append(product_data)
    
    if not listing_products:
        print("❌ No valid products found in listing database")
        return {
            **state,
            "shopify_status": {"success": False, "message": "No valid products found in listing database."}
        }
    
    # Convert listing database products to search result format for the parser
    working_search_results = []
    for listing_product in listing_products:
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
    
    # Build conversation context for the parser
    conversation_parts = []
    for msg in messages[-5:]:  # Only use last 5 messages to avoid old irrelevant context
        if hasattr(msg, 'content'):
            content = msg.content
            if isinstance(content, list):
                # Handle multimodal content
                text_parts = []
                for item in content:
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                content = " ".join(text_parts)
            # Only include messages that are relevant to product selection
            if content.strip() and not content.startswith("✅") and not content.startswith("🔄"):
                conversation_parts.append(f"{'User' if hasattr(msg, 'type') and msg.type == 'human' else 'Assistant'}: {content}")
    
    conversation_context = "\n".join(conversation_parts)
    
    # Use unified ProductSelectionIntentParser
    from .intent_parser_agent import product_selection_parser
    
    print("🤖 Using unified ProductSelectionIntentParser for product selection...")
    print(f"🔍 Debug - Current user query: '{user_query}'")
    print(f"🔍 Debug - Conversation context length: {len(conversation_context)} characters")
    if conversation_context:
        print(f"🔍 Debug - Conversation context preview: {conversation_context[:200]}...")
    
    selection_result = product_selection_parser.parse_product_selection(
        user_query=user_query,
        available_products=working_search_results,
        conversation_context=conversation_context
    )
    
    selected_products = selection_result.get("selected_products", [])
    selected_skus = selection_result.get("selected_skus", [])
    reasoning = selection_result.get("reasoning", "")
    confidence = selection_result.get("confidence", 0.0)
    
    print(f"🤖 Product Selection Result:")
    print(f"   Reasoning: {reasoning}")
    print(f"   Selected SKUs: {selected_skus}")
    print(f"   Confidence: {confidence}")
    
    if not selected_products:
        print("❌ No products selected for listing")
        return {
            **state,
            "shopify_status": {"success": False, "message": f"No products selected. {reasoning}"}
        }
    
    print(f"🔍 Found {len(selected_products)} products to process for Shopify")

    # Deduplicate by SKU
    unique_products = []
    seen_skus = set()
    for product in selected_products:
        sku = product.get('metadata', {}).get('sku', '')
        if sku and sku not in seen_skus:
            unique_products.append(product)
            seen_skus.add(sku)
    
    print(f"📦 Deduplicated to {len(unique_products)} unique products by SKU")
    
    # Process each product for Shopify listing
    successful_products = []
    failed_products = []
    
    for i, product in enumerate(unique_products, 1):
        metadata = product.get('metadata', {})
        sku = metadata.get('sku', '')
        
        print(f"🔄 Processing product {i}/{len(unique_products)}: {sku}")
        
        try:
            # Generate AI title and description
            ai_title = generate_ai_title(metadata, language)
            ai_description = generate_ai_description(metadata, language)
            
            print(f"🤖 Generated AI Title: {ai_title}")
            print(f"🤖 Generated AI Description: {ai_description[:100]}...")
            
            # Check listing database for modified images
            print(f"🔍 Debug - Checking listing database for SKU {sku}")
            listing_product = db.get_product(sku)
            print(f"🔍 Debug - Listing product found: {listing_product is not None}")
            
            if listing_product:
                print(f"🔍 Debug - Listing product keys: {list(listing_product.keys())}")
                listing_images = listing_product.get('listing_images', {})
                print(f"🔍 Debug - Has listing_images: {listing_images is not None}")
                
                if listing_images:
                    print(f"🔍 Debug - listing_images keys: {list(listing_images.keys())}")
                    all_images = listing_images.get('all_images', [])
                    print(f"🔍 Debug - all_images count: {len(all_images)}")
                    
                    if all_images:
                        print(f"🎨 Shopify Agent: Using {len(all_images)} images from listing database for SKU {sku}")
                        primary_image = listing_images.get('primary_image', '')
                        print(f"🎨 Primary image: {primary_image}")
                        
                        # Format media for Shopify API
                        media = [
                            {"originalSource": image_url, "mediaContentType": "IMAGE"}
                            for image_url in all_images
                        ]
                        
                        print(f"📸 Final media count for SKU {sku}: {len(media)} images")
                    else:
                        print(f"⚠️ No images found in listing database for SKU {sku}")
                        media = create_media_from_metadata(metadata)
                else:
                    print(f"⚠️ No listing_images found for SKU {sku}")
                    media = create_media_from_metadata(metadata)
            else:
                print(f"⚠️ No listing database entry found for SKU {sku}")
                media = create_media_from_metadata(metadata)
            
            # Create product input
            product_input = create_product_input_from_metadata(metadata, ai_title, ai_description)
            
            # Publish to Shopify
            result = publish_product_to_shopify(product_input, media, metadata)
            
            if result.get("success"):
                print(f"✅ Successfully published: {ai_title}")
                successful_products.append({
                    "title": ai_title,
                    "url": result.get("live_url", ""),
                    "sku": sku
                })
            else:
                error_msg = result.get("error", "Unknown error")
                print(f"❌ Failed to publish: {ai_title}")
                print(f"❌ Error details: {error_msg}")
                failed_products.append({
                    "title": ai_title,
                    "error": error_msg,
                    "sku": sku
                })
                
        except Exception as e:
            print(f"❌ Error processing product {sku}: {e}")
            failed_products.append({
                "title": f"Product {sku}",
                "error": str(e),
                "sku": sku
            })
    
    # Generate response
    response = generate_shopify_response(successful_products, failed_products, len(unique_products))
    
    # Format successful products for streaming response
    product_links = []
    for product in successful_products:
        product_links.append({
            "title": product["title"],
            "url": product.get("url", ""),
            "sku": product["sku"]
        })
    
    # Create streaming-friendly response message
    if successful_products:
        # Success response with product links
        response_message = f"🎉 Successfully listed {len(successful_products)} product(s) on Shopify!\n\n"
        for i, product in enumerate(successful_products, 1):
            response_message += f"**{i}. {product['title']}**\n"
            response_message += f"SKU: {product['sku']}\n"
            if product.get('url'):
                response_message += f"🔗 [View on Shopify]({product['url']})\n"
            response_message += "\n"
        
        if failed_products:
            response_message += f"⚠️ {len(failed_products)} product(s) failed to list:\n"
            for product in failed_products:
                response_message += f"- {product['title']}: {product.get('error', 'Unknown error')}\n"
    else:
        # Failure response
        response_message = f"❌ Failed to list any products on Shopify.\n\n"
        for product in failed_products:
            response_message += f"- {product['title']}: {product.get('error', 'Unknown error')}\n"
    
    return {
        **state,
        "shopify_status": {
            "success": len(successful_products) > 0,
            "message": response,
            "successful_count": len(successful_products),
            "failed_count": len(failed_products)
        },
        "product_links": product_links,
        "messages": [AIMessage(content=response_message)]
    }

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
    """
    Create a list of media dicts for Shopify from product metadata and modified images.
    Ensures all images are under 25MP and compresses if needed.
    The modified image (if present) is always the primary image.
    """
    media = []
    sku = metadata.get('sku', '')
    main_image_url = metadata.get('main_image_url', '')
    image_urls = metadata.get('image_urls', [])
    modified_image_url = None
    if modified_images:
        # Use the most recent modified image as primary
        modified_image_url = modified_images[0]["url"] if modified_images else None

    # Add modified image as primary if present
    if modified_image_url:
        # Validate and compress image resolution
        is_valid, validation_msg = validate_image_resolution(modified_image_url)
        if not is_valid:
            print(f"⚠️ Warning: Modified image for SKU {sku} exceeds 25MP limit: {validation_msg}")
            print(f"🔄 Compressing modified image before Shopify upload...")
            compressed_url = compress_image_url(modified_image_url)
            if compressed_url != modified_image_url:
                print(f"✅ Modified image compressed successfully for Shopify upload")
                modified_image_url = compressed_url
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
                # Validate and compress image resolution
                is_valid, validation_msg = validate_image_resolution(img_url)
                if not is_valid:
                    print(f"⚠️ Warning: Original image for SKU {sku} exceeds 25MP limit: {validation_msg}")
                    print(f"🔄 Compressing original image before Shopify upload...")
                    compressed_url = compress_image_url(img_url)
                    if compressed_url != img_url:
                        print(f"✅ Original image compressed successfully for Shopify upload")
                        img_url = compressed_url
                media.append({
                    "originalSource": img_url.strip(),
                    "mediaContentType": "IMAGE"
                })
    # Fallback to main_image_url if image_urls is not available and no modified image
    elif main_image_url and not modified_image_url:
        # Validate and compress image resolution
        is_valid, validation_msg = validate_image_resolution(main_image_url)
        if not is_valid:
            print(f"⚠️ Warning: Main image for SKU {sku} exceeds 25MP limit: {validation_msg}")
            print(f"🔄 Compressing main image before Shopify upload...")
            compressed_url = compress_image_url(main_image_url)
            if compressed_url != main_image_url:
                print(f"✅ Main image compressed successfully for Shopify upload")
                main_image_url = compressed_url
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
    print(f"📸 Final media count for SKU {sku}: {len(unique_media)} images")
    return unique_media

def publish_product_to_shopify(product_input: Dict[str, Any], media: List[Dict[str, str]], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use the existing shopify_listing.py logic to publish a product
    Returns: {'success': bool, 'title': str, 'live_url': str, 'product_id': str, 'error': str}
    """
    try:
        print(f"🔄 Starting Shopify publish for product: {product_input.get('title', 'Unknown')}")
        print(f"🔄 Media count: {len(media)}")
        
        url = f"https://{SHOP}/admin/api/2025-04/graphql.json"
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": ACCESS_TOKEN
        }
        
        # Step 1: Get Online Store publication ID
        print("🔄 Step 1: Getting Online Store publication ID...")
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
        
        if result.get("errors"):
            raise Exception(f"Publications query error: {result['errors']}")
        
        # Find the Online Store publication
        publication_id = None
        for edge in result["data"]["publications"]["edges"]:
            if "Online Store" in edge["node"]["name"]:
                publication_id = edge["node"]["id"]
                break
        
        if not publication_id:
            raise Exception("Online Store publication ID not found!")
        
        print(f"✅ Found publication ID: {publication_id}")
        
        # Step 2: Create Product
        print("🔄 Step 2: Creating product...")
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
        print(f"✅ Product created with ID: {product_id}")
        
        # Step 3: Publish the product
        print("🔄 Step 3: Publishing product...")
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
        
        print("✅ Product published successfully")
        
        # Step 4: Get default location ID
        print("🔄 Step 4: Getting location ID...")
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
        print(f"✅ Found location ID: {location_id}")
        
        # Step 5: Update variant with SKU, price, and inventory
        print("🔄 Step 5: Updating variant...")
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
        
        print("✅ Variant updated successfully")
        
        # Step 6: Get the live product URL
        print("🔄 Step 6: Getting product URL...")
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
        
        print(f"✅ Product URL: {live_url}")
        
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
        print(f"❌ Shopify publish failed: {str(e)}")
        return {
            'success': False,
            'title': product_input.get('title', 'Unknown'),
            'error': str(e)
        }

def generate_ai_title(metadata: Dict[str, Any], language: str = "en") -> str:
    """Generate AI-written product title."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7, request_timeout=15)
    
    product_data = f"""
SKU: {metadata.get('sku', 'N/A')}
Category: {metadata.get('category', 'N/A')}
Material: {metadata.get('material', 'N/A')}
Color: {metadata.get('color', 'N/A')}
Features: {metadata.get('characteristics_text', 'N/A')}
Dimensions: Height: {metadata.get('height', 'N/A')}\", Width: {metadata.get('width', 'N/A')}\", Length: {metadata.get('length', 'N/A')}\"
Weight: {metadata.get('weight', 'N/A')} lbs
Scene: {metadata.get('scene', 'N/A')}
"""
    
    if language == "zh":
        title_prompt = f"""
为这个产品创建一个吸引人的、SEO友好的产品标题。让它具有吸引力且描述性强。

产品信息:
{product_data}

要求:
- 保持在100个字符以内
- 包含关键特性，如材质、颜色或类型
- 对客户有吸引力
- 不要在标题中包含SKU
- 要具体且描述性强

标题:"""
    else:
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
    return title_response.content.strip().strip('"').strip("'")

def generate_ai_description(metadata: Dict[str, Any], language: str = "en") -> str:
    """Generate AI-written product description."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7, request_timeout=15)
    
    product_data = f"""
SKU: {metadata.get('sku', 'N/A')}
Category: {metadata.get('category', 'N/A')}
Material: {metadata.get('material', 'N/A')}
Color: {metadata.get('color', 'N/A')}
Features: {metadata.get('characteristics_text', 'N/A')}
Dimensions: Height: {metadata.get('height', 'N/A')}\", Width: {metadata.get('width', 'N/A')}\", Length: {metadata.get('length', 'N/A')}\"
Weight: {metadata.get('weight', 'N/A')} lbs
Scene: {metadata.get('scene', 'N/A')}
"""
    
    if language == "zh":
        desc_prompt = f"""
为这个产品创建一个吸引人的产品描述。让它引人入胜且信息丰富。

产品信息:
{product_data}

要求:
- 写2-3段
- 突出关键特性和优势
- 对客户有吸引力
- 包含实际使用场景
- 热情但专业
- 不要在描述中包含SKU

描述:"""
    else:
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
    return desc_response.content.strip()

def generate_shopify_response(successful_products: List[Dict], failed_products: List[Dict], total_count: int) -> str:
    """Generate a friendly response message for Shopify listing results."""
    if not successful_products:
        return "❌ No products were successfully published to Shopify."
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3, request_timeout=10)
    
    # Check if any product has Chinese characters to determine language
    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in str(successful_products))
    language = "zh" if has_chinese else "en"
    
    links_str = "\n".join([f"- {p['title']}: {p['url']}" for p in successful_products])
    
    if language == "zh":
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
    
    return llm.invoke(prompt).content
