#!/usr/bin/env python3
"""
Test script for the image agent functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langgraph_workflow.nodes.image_agent import ImageAgent
import config

def test_image_agent():
    """Test the image agent with a sample image"""
    
    print("🧪 Testing Image Agent...")
    
    # Initialize the image agent
    agent = ImageAgent()
    
    # Test image URL (you can replace this with any image URL)
    test_image_url = "https://replicate.delivery/pbxt/N55l5TWGh8mSlNzW8usReoaNhGbFwvLeZR3TX1NL4pd2Wtfv/replicate-prediction-f2d25rg6gnrma0cq257vdw2n4c.png"
    test_instruction = "Make this a 90s cartoon style"
    
    print(f"🎨 Testing with image: {test_image_url}")
    print(f"🎨 Instruction: {test_instruction}")
    
    try:
        # Test the image modification
        result = agent.modify_image(test_image_url, test_instruction)
        
        print("\n📊 Results:")
        print(f"Status: {result.get('status')}")
        print(f"Original Image: {result.get('original_image_url')}")
        print(f"Modified Image: {result.get('modified_image_url')}")
        print(f"Instruction: {result.get('instruction')}")
        
        if result.get('status') == 'success':
            print("✅ Image modification successful!")
        else:
            print(f"❌ Image modification failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")

if __name__ == "__main__":
    test_image_agent() 