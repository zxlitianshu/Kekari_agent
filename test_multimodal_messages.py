#!/usr/bin/env python3
"""
Test script for multimodal message handling in the API.
"""

import requests
import json
import base64

# API endpoint
API_BASE = "http://localhost:8000"

def test_text_only_message():
    """Test a simple text-only message."""
    print("🧪 Testing text-only message...")
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Hello, how are you?"
            }
        ],
        "session_id": "test_session_1"
    }
    
    response = requests.post(f"{API_BASE}/v1/chat/completions/json", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Text-only message successful: {result['choices'][0]['message']['content'][:100]}...")
        return True
    else:
        print(f"❌ Text-only message failed: {response.status_code} - {response.text}")
        return False

def test_multimodal_message():
    """Test a multimodal message with text and image."""
    print("🧪 Testing multimodal message...")
    
    # Create a simple base64 image (1x1 pixel)
    simple_image = base64.b64encode(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9').decode()
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "put these two chairs in a coffee shop"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{simple_image}"
                        }
                    }
                ]
            }
        ],
        "session_id": "test_session_2"
    }
    
    response = requests.post(f"{API_BASE}/v1/chat/completions/json", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Multimodal message successful: {result['choices'][0]['message']['content'][:100]}...")
        return True
    else:
        print(f"❌ Multimodal message failed: {response.status_code} - {response.text}")
        return False

def test_models_endpoint():
    """Test the models endpoint."""
    print("🧪 Testing models endpoint...")
    
    response = requests.get(f"{API_BASE}/v1/models")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Models endpoint successful: {result}")
        return True
    else:
        print(f"❌ Models endpoint failed: {response.status_code} - {response.text}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting multimodal message tests...")
    
    # Test models endpoint first
    if not test_models_endpoint():
        print("❌ Models endpoint test failed, stopping tests.")
        return
    
    # Test text-only message
    if not test_text_only_message():
        print("❌ Text-only message test failed.")
        return
    
    # Test multimodal message
    if not test_multimodal_message():
        print("❌ Multimodal message test failed.")
        return
    
    print("🎉 All tests passed!")

if __name__ == "__main__":
    main() 