#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langgraph_workflow.nodes.intent_parser_agent import IntentParserAgent
import json

def debug_intent_parser_data():
    """Debug what data is actually being passed to the intent parser"""
    
    # Simulate the exact data structure from the logs
    search_results = [
        {
            "id": "W24183624_text",
            "score": 0.395757556,
            "metadata": {
                "US": True,
                "category": "Patio Seating",
                "category_code": 10158.0,
                "characteristics_text": "1.Packing: 1 pcs /ctn 2.Item Dimensions: 29.53\"L x 29.53 \"W x 29.53 \"H, Load-bearing capacity:120lbs 3.Material:The square table is made of high-quality steel, making it lightweight and easy to carry...",
                "color": "Black",
                "height": 29.53,
                "image_urls": ["https://b2bfiles1.gigab2b.cn/image/wkseller/135/20230604_8a89b26951bf2c4c1f18d97851d83a0b.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=3836c2207b5c12227018ef3657d5def1"],
                "length": 29.53,
                "length_cm": 75.0,
                "main_image_url": "https://b2bfiles1.gigab2b.cn/image/wkseller/135/20230604_8a89b26951bf2c4c1f18d97851d83a0b.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=3836c2207b5c12227018ef3657d5def1",
                "material": "Steel",
                "scene": "None",
                "sku": "W24183624",
                "total_images": 20.0,
                "type": "text",
                "weight": 15.43,
                "weight_kg": 7.0,
                "width": 29.53
            },
            "values": []
        },
        {
            "id": "W87470711_text",
            "score": 0.395757556,
            "metadata": {
                "US": True,
                "category": "Patio Seating",
                "category_code": 10158.0,
                "characteristics_text": "1.Packing: 1 pcs /ctn 2.Item Dimensions: 46.85\"L x 29.53 \"W x 29.53 \"H, Load-bearing capacity:120lbs 3.Material:The square table is made of high-quality rattan, making it lightweight and easy to carry...",
                "color": "Brown",
                "height": 29.53,
                "image_urls": ["https://b2bfiles1.gigab2b.cn/image/wkseller/7562/20230515_5ee66a37c84518c5871eb8f348668655.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=2caa0d17a005522caf7916f475afc9e8"],
                "length": 46.85,
                "length_cm": 119.0,
                "main_image_url": "https://b2bfiles1.gigab2b.cn/image/wkseller/7562/20230515_5ee66a37c84518c5871eb8f348668655.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=2caa0d17a005522caf7916f475afc9e8",
                "material": "Rattan",
                "scene": "None",
                "sku": "W87470711",
                "total_images": 14.0,
                "type": "text",
                "weight": 26.46,
                "weight_kg": 12.0,
                "width": 29.53
            },
            "values": []
        },
        {
            "id": "W24172223_text",
            "score": 0.395757556,
            "metadata": {
                "US": True,
                "category": "Patio Seating",
                "category_code": 10158.0,
                "characteristics_text": "1.Packing: 1 pcs /ctn 2.Item Dimensions: 27.56\"L x 27.56 \"W x 27.56 \"H, Load-bearing capacity:120lbs 3.Material:The square table is made of high-quality aluminum, making it lightweight and easy to carry...",
                "color": "Black",
                "height": 4.72,
                "image_urls": ["https://b2bfiles1.gigab2b.cn/image/wkseller/135/20230601_59711d0e468561e8c49c94142e65d4ee.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=d88ca0a504be86ef6eab5aacaee9c316"],
                "length": 27.55,
                "length_cm": 69.98,
                "main_image_url": "https://b2bfiles1.gigab2b.cn/image/wkseller/135/20230601_59711d0e468561e8c49c94142e65d4ee.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=d88ca0a504be86ef6eab5aacaee9c316",
                "material": "Aluminum",
                "scene": "None",
                "sku": "W24172223",
                "total_images": 20.0,
                "type": "text",
                "weight": 8.86,
                "weight_kg": 4.02,
                "width": 8.66
            },
            "values": []
        }
    ]
    
    # Simulate the conversation context from the logs
    conversation_context = """User: 帮我看看有没有适合户外场景的产品，需要有货，美国的，重量低于80kg
Assistant: 我找到了一些适合户外场景的产品，重量都低于80公斤，并且在美国有货。以下是详细信息：

**SKU:** W24183624  
![Product Image](https://b2bfiles1.gigab2b.cn/image/wkseller/135/20230604_8a89b26951bf2c4c1f18d97851d83a0b.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=3836c2207b5c12227018ef3657d5def1)

**产品名称:** Patio Seating Set  
**类别:** Patio Seating  
**材质:** Steel  
**颜色:** Black  
**重量:** 15.43 lbs (7.0 kg)  
**尺寸:** Height: 29.53", Width: 29.53", Length: 29.53"  

**主要特点:** 这款户外座椅套装由高质量钢材制成，具有出色的耐用性和稳定性...

**SKU:** W87470711  
![Product Image](https://b2bfiles1.gigab2b.cn/image/wkseller/7562/20230515_5ee66a37c84518c5871eb8f348668655.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=2caa0d17a005522caf7916f475afc9e8)

**产品名称:** Rattan Patio Set  
**类别:** Patio Seating  
**材质:** Rattan  
**颜色:** Brown  
**重量:** 26.46 lbs (12.0 kg)  
**尺寸:** Height: 29.53", Width: 29.53", Length: 46.85"  

**主要特点:** 这款藤制户外套装采用天然藤条编织...

**SKU:** W24172223  
![Product Image](https://b2bfiles1.gigab2b.cn/image/wkseller/135/20230601_59711d0e468561e8c49c94142e65d4ee.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=d88ca0a504be86ef6eab5aacaee9c316)

**产品名称:** Aluminum Square Table  
**类别:** Patio Seating  
**材质:** Aluminum  
**颜色:** Black  
**重量:** 8.86 lbs (4.02 kg)  
**尺寸:** Height: 4.72", Width: 8.66", Length: 27.55"  

**主要特点:** 这款轻便的方桌由高质量铝制成，便于携带，防水防污..."""
    
    user_query = "这款铝制方桌不错，帮我改一下背景，换成一家人吃BBQ，桌子不变"
    
    print("🔍 Debug: Intent Parser Data Analysis")
    print("=" * 60)
    
    # Show what the intent parser will receive
    print(f"\n📝 User Query: {user_query}")
    print(f"\n📊 Search Results Count: {len(search_results)}")
    
    # Show the product mapping that will be created
    print(f"\n🏷️ Product Mapping:")
    for i, product in enumerate(search_results):
        metadata = product.get('metadata', {})
        print(f"  {i+1}. SKU: {metadata.get('sku', 'N/A')}")
        print(f"     Material: {metadata.get('material', 'N/A')}")
        print(f"     Category: {metadata.get('category', 'N/A')}")
        print(f"     Weight: {metadata.get('weight', 'N/A')} lbs")
        print(f"     Characteristics: {metadata.get('characteristics_text', 'N/A')[:100]}...")
        print()
    
    # Show what the LLM will see in the available products list
    print(f"\n📋 Available Products for LLM:")
    product_mapping = {}
    for i, product in enumerate(search_results):
        metadata = product.get('metadata', {})
        sku = metadata.get('sku', '')
        if sku:
            product_mapping[sku] = {
                'product': product,
                'index': i + 1,
                'sku': sku,
                'category': metadata.get('category', ''),
                'material': metadata.get('material', ''),
                'color': metadata.get('color', '')
            }
    
    # Use the same logic as the intent parser to generate names and summaries
    available_products_for_llm = []
    for i, mapping in enumerate(product_mapping.values()):
        product = mapping['product']
        metadata = product.get('metadata', {})
        
        # Try to get a descriptive name from various sources
        name = metadata.get('name', '')
        if not name:
            # Try to extract from characteristics_text
            characteristics = metadata.get('characteristics_text', '')
            if characteristics:
                # Look for material and type in characteristics
                material = metadata.get('material', '')
                category = metadata.get('category', '')
                if material and category:
                    name = f"{material} {category}"
                elif material:
                    name = f"{material} Product"
                else:
                    name = f"Product {metadata.get('sku', 'Unknown')}"
            else:
                # Fallback to material + category
                material = metadata.get('material', '')
                category = metadata.get('category', '')
                if material and category:
                    name = f"{material} {category}"
                else:
                    name = f"Product {metadata.get('sku', 'Unknown')}"
        
        # Create a rich summary with all available info
        summary_parts = []
        if metadata.get('category'):
            summary_parts.append(f"Category: {metadata.get('category')}")
        if metadata.get('material'):
            summary_parts.append(f"Material: {metadata.get('material')}")
        if metadata.get('color'):
            summary_parts.append(f"Color: {metadata.get('color')}")
        if metadata.get('weight'):
            summary_parts.append(f"Weight: {metadata.get('weight')} lbs")
        if metadata.get('characteristics_text'):
            # Take first 100 chars of characteristics
            chars = metadata.get('characteristics_text', '')[:100]
            summary_parts.append(f"Features: {chars}...")
        
        summary = ", ".join(summary_parts)
        
        available_products_for_llm.append({
            'index': i + 1,
            'sku': mapping['sku'],
            'name': name,
            'summary': summary
        })
    
    print(json.dumps(available_products_for_llm, indent=2, ensure_ascii=False))
    
    print(f"\n💬 Conversation Context Length: {len(conversation_context)} characters")
    print(f"💬 Last Assistant Listing: {conversation_context.split('Assistant:')[-1][:200]}...")
    
    # Now test the actual intent parser
    print(f"\n🧪 Testing Intent Parser with Real Data Structure")
    print("-" * 40)
    
    parser = IntentParserAgent()
    result = parser.parse_intent(
        user_query=user_query,
        available_products=search_results,
        conversation_context=conversation_context,
        action_type="image_modification"
    )
    
    print(f"✅ Selected SKUs: {result['selected_skus']}")
    print(f"🎯 Confidence: {result['confidence']}")
    print(f"💭 Reasoning: {result['reasoning']}")
    
    # Check if it correctly identified the aluminum table
    expected_sku = "W24172223"  # The aluminum table
    if expected_sku in result['selected_skus']:
        print(f"✅ SUCCESS: Correctly identified aluminum table (SKU: {expected_sku})")
    else:
        print(f"❌ FAILED: Did not identify aluminum table. Expected: {expected_sku}, Got: {result['selected_skus']}")

if __name__ == "__main__":
    debug_intent_parser_data() 