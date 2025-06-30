#!/usr/bin/env python3
"""
Test script for the integrated image processor functionality.
"""

import os
import requests
import tempfile
from PIL import Image
import uuid

def create_test_image():
    """Create a simple test image for testing."""
    # Create a simple test image
    img = Image.new('RGB', (300, 200), color='red')
    
    # Save to temporary file
    temp_dir = tempfile.mkdtemp()
    test_image_path = os.path.join(temp_dir, f"test_image_{uuid.uuid4()}.jpg")
    img.save(test_image_path)
    
    return test_image_path, temp_dir

def test_intent_analysis():
    """Test the intent analysis functionality."""
    print("🧠 Testing Intent Analysis")
    print("=" * 50)
    
    from langgraph_workflow.nodes.image_agent import analyze_image_request
    
    test_queries = [
        "Change the background to a coffee shop",
        "Make this a 90s cartoon style",
        "Upload this image and modify it",
        "Hello, how are you?",
        "Find me some products",
        "Process this photo with a vintage filter"
    ]
    
    for query in test_queries:
        analysis = analyze_image_request(query)
        print(f"Query: '{query}'")
        print(f"  Is image request: {analysis['is_image_request']}")
        print(f"  Approach: {analysis['approach']}")
        if analysis.get('instruction'):
            print(f"  Instruction: {analysis['instruction']}")
        print()

def test_api_endpoints():
    """Test the API endpoints."""
    print("🌐 Testing API Endpoints")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    # Test health check
    try:
        response = requests.get(f"{base_url}/info")
        print(f"Info endpoint: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ Info endpoint failed: {e}")
    
    # Test models endpoint
    try:
        response = requests.get(f"{base_url}/v1/models")
        print(f"Models endpoint: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ Models endpoint failed: {e}")

def test_file_upload_workflow():
    """Test the complete file upload and processing workflow."""
    print("📤 Testing File Upload Workflow")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    session_id = f"test_session_{uuid.uuid4()}"
    
    # Create test image
    test_image_path, temp_dir = create_test_image()
    
    try:
        # Step 1: Upload file
        print(f"📤 Uploading test image: {test_image_path}")
        with open(test_image_path, 'rb') as f:
            files = {'files': (os.path.basename(test_image_path), f, 'image/jpeg')}
            data = {'session_id': session_id}
            
            response = requests.post(f"{base_url}/v1/upload-files", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Upload successful: {result}")
            else:
                print(f"❌ Upload failed: {response.status_code} - {response.text}")
                return
        
        # Step 2: Send image processing request
        print(f"🎨 Sending image processing request")
        chat_data = {
            "messages": [
                {"role": "user", "content": "Change the background to a modern office with people working"}
            ],
            "session_id": session_id
        }
        
        response = requests.post(f"{base_url}/v1/chat/completions", json=chat_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Processing request successful")
            print(f"📝 Response: {result['choices'][0]['message']['content'][:200]}...")
        else:
            print(f"❌ Processing request failed: {response.status_code} - {response.text}")
    
    finally:
        # Cleanup
        try:
            os.remove(test_image_path)
            os.rmdir(temp_dir)
        except:
            pass

def test_product_image_workflow():
    """Test the product image modification workflow."""
    print("🛍️ Testing Product Image Workflow")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    session_id = f"test_session_{uuid.uuid4()}"
    
    # Step 1: Search for products
    print("🔍 Searching for products")
    chat_data = {
        "messages": [
            {"role": "user", "content": "Find me some products for a coffee shop"}
        ],
        "session_id": session_id
    }
    
    response = requests.post(f"{base_url}/v1/chat/completions", json=chat_data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Product search successful")
        print(f"📝 Response: {result['choices'][0]['message']['content'][:200]}...")
        
        # Step 2: Modify product image
        print("🎨 Modifying product image")
        chat_data = {
            "messages": [
                {"role": "user", "content": "Change the background of the first product to a coffee shop"}
            ],
            "session_id": session_id
        }
        
        response = requests.post(f"{base_url}/v1/chat/completions", json=chat_data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Image modification successful")
            print(f"📝 Response: {result['choices'][0]['message']['content'][:200]}...")
        else:
            print(f"❌ Image modification failed: {response.status_code} - {response.text}")
    else:
        print(f"❌ Product search failed: {response.status_code} - {response.text}")

def main():
    """Main test function."""
    print("🧪 Integrated Image Processor Test Suite")
    print("=" * 60)
    
    # Test 1: Intent Analysis
    test_intent_analysis()
    
    # Test 2: API Endpoints
    test_api_endpoints()
    
    # Test 3: File Upload Workflow (requires S3 setup)
    print("\n⚠️  File upload workflow requires S3_BUCKET_NAME environment variable")
    print("⚠️  and AWS credentials to be configured")
    # test_file_upload_workflow()
    
    # Test 4: Product Image Workflow
    test_product_image_workflow()
    
    print("\n✅ Test suite complete!")

if __name__ == "__main__":
    main() 