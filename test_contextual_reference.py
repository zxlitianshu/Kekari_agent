#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langgraph_workflow.nodes.intent_parser_agent import IntentParserAgent

def test_contextual_reference():
    """Test the intent parser with the exact scenario from the logs"""
    
    # Sample search results (like what would come from product search)
    search_results = [
        {
            "metadata": {
                "sku": "W24183624",
                "name": "Patio Seating Set",
                "category": "Patio Seating",
                "material": "Steel",
                "color": "Black"
            }
        },
        {
            "metadata": {
                "sku": "W87470711",
                "name": "Rattan Patio Seating",
                "category": "Patio Seating", 
                "material": "Rattan",
                "color": "khaki"
            }
        },
        {
            "metadata": {
                "sku": "W24172223",
                "name": "Aluminum Square Table",
                "category": "Patio Seating",
                "material": "Aluminum", 
                "color": "Black"
            }
        }
    ]
    
    # Simulate the conversation context from the real workflow
    conversation_context = """User: 帮我看看有没有适合户外场景的产品，需要有货，美国的，重量低于80kg
Assistant: 我找到了几款适合户外场景的产品，重量都低于80公斤，并且在美国有货。以下是详细信息：

**SKU:** W24183624  
![Product Image](https://b2bfiles1.gigab2b.cn/image/wkseller/135/20230604_8a89b26951bf2c4c1f18d97851d83a0b.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=3836c2207b5c12227018ef3657d5def1)

**SKU:** W87470711  
![Product Image](https://b2bfiles1.gigab2b.cn/image/wkseller/7562/20230515_5ee66a37c84518c5871eb8f348668655.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=2caa0d17a005522caf7916f475afc9e8)

**SKU:** W24172223  
![Product Image](https://b2bfiles1.gigab2b.cn/image/wkseller/135/20230601_59711d0e468561e8c49c94142e65d4ee.jpg?x-cc=20&x-cu=72225&x-ct=1750834800&x-cs=d88ca0a504be86ef6eab5aacaee9c316)"""
    
    # Test the exact user query from the logs
    test_cases = [
        {
            "query": "这款铝制方桌不错，帮我改一下背景，换成一家人吃BBQ，桌子不变",
            "expected_skus": ["W24172223"],  # Should select only the aluminum table
            "description": "User refers to 'this aluminum square table'"
        },
        {
            "query": "这款不错，帮我做一张图，背景是一家人吃bbq，桌椅不变",
            "expected_skus": ["W24172223"],  # Should select the most recent/mentioned table
            "description": "User refers to 'this one' (most recent product)"
        },
        {
            "query": "第一个产品不错，帮我改背景",
            "expected_skus": ["W24183624"],  # Should select the first product
            "description": "User refers to 'first product'"
        }
    ]
    
    parser = IntentParserAgent()
    
    print("🧪 Testing Intent Parser with Contextual References")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test Case {i}: {test_case['description']}")
        print(f"🎯 Query: {test_case['query']}")
        print(f"🎯 Expected SKUs: {test_case['expected_skus']}")
        
        result = parser.parse_intent(
            user_query=test_case['query'],
            available_products=search_results,
            conversation_context=conversation_context,
            action_type="image_modification"
        )
        
        print(f"✅ Selected SKUs: {result['selected_skus']}")
        print(f"🎯 Confidence: {result['confidence']}")
        print(f"💭 Reasoning: {result['reasoning']}")
        
        # Check if we got the expected results
        if set(result['selected_skus']) == set(test_case['expected_skus']):
            print("✅ PASS: Intent parser correctly identified products")
        else:
            print("❌ FAIL: Intent parser did not identify expected products")
            print(f"   Expected: {test_case['expected_skus']}")
            print(f"   Got: {result['selected_skus']}")
        
        print("-" * 40)

if __name__ == "__main__":
    test_contextual_reference() 