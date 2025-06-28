import os
import time
import requests
from typing import Dict, List, Any
import replicate
from langchain_core.messages import HumanMessage, AIMessage
import config

class ImageAgent:
    def __init__(self):
        self.replicate_client = replicate.Client(api_token=config.REPLICATE_API_TOKEN)
        self.modified_images_storage = {}  # In-memory storage for demo
    
    def modify_image(self, image_url: str, instruction: str, output_format: str = "jpg") -> Dict[str, Any]:
        """
        Modify an image based on text instruction using Replicate's Flux model
        
        Args:
            image_url: URL of the source image
            instruction: Text instruction for modification (e.g., "Make this a 90s cartoon", "Change background to coffee shop")
            output_format: Output format (jpg, png, etc.)
            
        Returns:
            Dict containing modified image URL and metadata
        """
        try:
            print(f"🎨 Image Agent: Modifying image with instruction: '{instruction}'")
            print(f"🎨 Image Agent: Source image: {image_url}")
            
            # Use Flux Kontext Pro model for image modification
            input_data = {
                "prompt": instruction,
                "input_image": image_url,
                "output_format": output_format
            }
            
            # Run the model
            output = self.replicate_client.run(
                "black-forest-labs/flux-kontext-pro",
                input=input_data
            )
            
            # FIX: Convert FileOutput to string URL for serialization
            if hasattr(output, 'url'):
                modified_image_url = str(output.url)
            elif isinstance(output, str):
                modified_image_url = output
            else:
                # Try to convert to string
                modified_image_url = str(output)
            
            # Store the modified image info
            result = {
                "original_image_url": image_url,
                "modified_image_url": modified_image_url,
                "instruction": instruction,
                "status": "success",
                "timestamp": time.time()
            }
            
            print(f"✅ Image Agent: Successfully modified image")
            print(f"✅ Image Agent: Modified image URL: {modified_image_url}")
            
            return result
            
        except Exception as e:
            print(f"❌ Image Agent: Error modifying image: {str(e)}")
            return {
                "original_image_url": image_url,
                "modified_image_url": None,
                "instruction": instruction,
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def batch_modify_images(self, images: List[Dict], instruction: str) -> List[Dict]:
        """
        Modify multiple images with the same instruction
        
        Args:
            images: List of image dictionaries with 'url' and 'sku' keys
            instruction: Text instruction for modification
            
        Returns:
            List of modification results
        """
        results = []
        for image_info in images:
            image_url = image_info.get('url')
            sku = image_info.get('sku', 'unknown')
            
            if image_url:
                print(f"🎨 Image Agent: Processing image for SKU: {sku}")
                result = self.modify_image(image_url, instruction)
                result['sku'] = sku
                results.append(result)
            else:
                print(f"⚠️ Image Agent: No URL found for SKU: {sku}")
        
        return results

def image_agent_node(state):
    """
    LangGraph node for image modification with intent parsing
    
    Expects state to contain:
    - parsed_intent: Dict with selected products from intent parser
    - image_modification_request: Dict with 'instruction'
    - search_results: List of products (for context)
    - incorporate_previous: Boolean flag to incorporate previous modification
    
    Returns state with:
    - modified_images: List of modified image results
    - image_agent_response: Summary of modifications
    - awaiting_confirmation: Boolean to indicate waiting for user confirmation
    """
    print("🔄 LangGraph: Executing 'image_agent' node...")
    
    # Debug: Log what we received in state
    print(f"🔍 Image Agent Debug - image_modification_request: {state.get('image_modification_request')}")
    print(f"🔍 Image Agent Debug - parsed_intent: {state.get('parsed_intent')}")
    print(f"🔍 Image Agent Debug - search_results length: {len(state.get('search_results', []))}")
    print(f"🔍 Image Agent Debug - incorporate_previous: {state.get('incorporate_previous')}")
    
    # Initialize the image agent
    agent = ImageAgent()
    
    # Get the modification request and parsed intent from state
    modification_request = state.get("image_modification_request", {})
    parsed_intent = state.get("parsed_intent", {})
    search_results = state.get("search_results", [])
    incorporate_previous = state.get("incorporate_previous", False)
    
    # If we need to incorporate previous modifications, do that first
    if incorporate_previous:
        print("🔄 Image Agent: Incorporating previous modifications...")
        from .listing_database import ListingDatabase
        db = ListingDatabase()
        
        # Get any pending modifications from state
        pending_modifications = state.get("modified_images", [])
        if pending_modifications:
            for mod in pending_modifications:
                if mod.get('status') == 'success':
                    sku = mod.get('sku')
                    modified_image_url = mod.get('modified_image_url')
                    instruction = mod.get('instruction')
                    
                    if sku and modified_image_url:
                        print(f"✅ Image Agent: Incorporating modification for SKU {sku}")
                        db.add_product(sku, {
                            'modified_image_url': modified_image_url,
                            'modification_instruction': instruction,
                            'timestamp': time.time()
                        })
        
        # Clear the incorporate_previous flag
        state["incorporate_previous"] = False
    
    if not modification_request:
        return {
            **state,
            "modified_images": [],
            "image_agent_response": "No image modification request found.",
            "awaiting_confirmation": False
        }
    
    # Extract request details
    instruction = modification_request.get("instruction", "")
    
    if not instruction:
        return {
            **state,
            "modified_images": [],
            "image_agent_response": "No modification instruction provided.",
            "awaiting_confirmation": False
        }
    
    # Use parsed intent to get selected products
    selected_products = parsed_intent.get("selected_products", [])
    selected_skus = parsed_intent.get("selected_skus", [])
    reasoning = parsed_intent.get("reasoning", "")
    confidence = parsed_intent.get("confidence", 0.0)
    
    print(f"🎯 Image Agent: Using intent parser results")
    print(f"🎯 Image Agent: Selected SKUs: {selected_skus}")
    print(f"🎯 Image Agent: Confidence: {confidence}")
    print(f"🎯 Image Agent: Reasoning: {reasoning}")
    
    if not selected_products:
        # Fallback: if no products selected by intent parser, use all available products
        print("⚠️ Image Agent: No products selected by intent parser, using all available products")
        selected_products = search_results.copy() if search_results else []
        selected_skus = [product.get('metadata', {}).get('sku', '') for product in selected_products]
        selected_skus = [sku for sku in selected_skus if sku]
    
    if not selected_products:
        return {
            **state,
            "modified_images": [],
            "image_agent_response": "No products found to modify images for.",
            "awaiting_confirmation": False
        }
    
    # Process each selected product
    modification_results = []
    successful_modifications = []
    failed_modifications = []
    
    for i, product in enumerate(selected_products, 1):
        metadata = product.get('metadata', {})
        sku = metadata.get('sku', f'unknown_{i}')
        
        print(f"🎨 Image Agent: Processing product {i}/{len(selected_products)}: {sku}")
        
        # Get the main image URL
        image_url = metadata.get('main_image_url') or metadata.get('image_url')
        
        # If still no image, try to get from image_urls array
        if not image_url:
            image_urls = metadata.get('image_urls', [])
            if image_urls:
                image_url = image_urls[0]
        
        if not image_url:
            print(f"⚠️ Image Agent: No image found for SKU: {sku}")
            failed_modifications.append({
                'sku': sku,
                'reason': 'No image URL found',
                'status': 'error'
            })
            continue
        
        # Modify the image
        modification_result = agent.modify_image(image_url, instruction)
        modification_result['sku'] = sku
        modification_result['product_index'] = i
        
        if modification_result['status'] == 'success':
            successful_modifications.append(modification_result)
            modification_results.append(modification_result)
        else:
            failed_modifications.append(modification_result)
    
    # Create response based on results
    if successful_modifications:
        # Show the first successful modification for confirmation
        first_result = successful_modifications[0]
        
        response_text = f"""🎨 **Image Modification Complete!**

I've successfully modified images for **{len(successful_modifications)} product(s)** with your instruction: *"{instruction}"*

**Products Modified:**
{chr(10).join([f"• SKU {result['sku']} (Product {result['product_index']})" for result in successful_modifications])}

**Sample Result (SKU {first_result['sku']}):**

**Original Image:**
![Original]({first_result['original_image_url']})

**Modified Image:**
![Modified]({first_result['modified_image_url']})

{f"**Failed Modifications:** {len(failed_modifications)} products" if failed_modifications else ""}

**Would you like me to incorporate these modified images into the official listing preparation database?** 

This will:
- Set the modified images as the front/primary images for these products
- Keep all other original images as additional views
- Make them ready for Shopify listing with the new backgrounds

Please respond with:
- **"Yes"** or **"Yes, incorporate them"** to add them to the listing database
- **"No"** to discard the modifications
- **"Show me more"** to see other modified images before deciding"""
        
        if failed_modifications:
            response_text += f"\n\n**Note:** {len(failed_modifications)} products failed to modify due to missing images or errors."
        
    else:
        response_text = f"""❌ **Image Modification Failed**

I was unable to modify any images with your instruction: *"{instruction}"*

**Issues encountered:**
{chr(10).join([f"• SKU {result['sku']}: {result.get('reason', 'Unknown error')}" for result in failed_modifications])}

Please check that the products have valid images and try again."""
    
    return {
        **state,
        "modified_images": modification_results,
        "image_agent_response": response_text,
        "awaiting_confirmation": len(successful_modifications) > 0,
        "successful_modifications": successful_modifications,
        "failed_modifications": failed_modifications
    } 