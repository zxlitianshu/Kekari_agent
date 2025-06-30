#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langgraph_workflow.nodes.intent_parser_agent import IntentParserAgent
from langchain_core.messages import HumanMessage

def test_intent_parser():
    """Test the intent parser with sample data"""
    
    # Sample search results (like what would come from product search)
    search_results = [
        {
            "metadata": {
                "sku": "CHAIR001",
                "name": "Wooden Office Chair",
                "category": "chair",
                "material": "wood",
                "color": "brown"
            }
        },
        {
            "metadata": {
                "sku": "TABLE001", 
                "name": "Glass Coffee Table",
                "category": "table",
                "material": "glass",
                "color": "clear"
            }
        },
        {
            "metadata": {
                "sku": "CHAIR002",
                "name": "Leather Gaming Chair", 
                "category": "chair",
                "material": "leather",
                "color": "black"
            }
        }
    ]
    
    # Test cases
    test_cases = [
        {
            "query": "Modify the first chair to have a coffee shop background",
            "action_type": "image_modification",
            "expected_skus": ["CHAIR001"]
        },
        {
            "query": "Change the background of the second product to an office",
            "action_type": "image_modification", 
            "expected_skus": ["TABLE001"]
        },
        {
            "query": "Modify both chairs to have a modern living room background",
            "action_type": "image_modification",
            "expected_skus": ["CHAIR001", "CHAIR002"]
        },
        {
            "query": "Put the gaming chair in a coffee shop",
            "action_type": "image_modification",
            "expected_skus": ["CHAIR002"]
        }
    ]
    
    parser = IntentParserAgent()
    
    print("🧪 Testing Intent Parser for Image Agent Workflow")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test Case {i}: {test_case['query']}")
        print(f"🎯 Expected SKUs: {test_case['expected_skus']}")
        
        result = parser.parse_intent(
            user_query=test_case['query'],
            available_products=search_results,
            conversation_context="",
            action_type=test_case['action_type']
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
    test_intent_parser() 