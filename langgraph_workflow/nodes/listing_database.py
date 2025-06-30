import json
import os
import requests
from PIL import Image
from io import BytesIO
from typing import Dict, List, Any
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage

def extract_text_from_multimodal_content(content):
    """Extract text content from multimodal messages, handling images properly."""
    if isinstance(content, str):
        return content
    
    if isinstance(content, list):
        text_parts = []
        image_count = 0
        
        for item in content:
            if item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif item.get("type") == "image_url":
                image_count += 1
        
        # Combine text parts
        text_content = " ".join(text_parts)
        
        # Add image indicator if images are present
        if image_count > 0:
            text_content += f" [User has uploaded {image_count} image(s)]"
        
        return text_content
    
    return str(content)

def validate_image_resolution(image_url: str, max_megapixels: int = 25) -> tuple[bool, str]:
    """
    Validate if an image exceeds the maximum resolution limit.
    
    Args:
        image_url: URL of the image to validate
        max_megapixels: Maximum allowed megapixels (default 25)
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        # Download the image
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Open with PIL to get dimensions
        img = Image.open(BytesIO(response.content))
        width, height = img.size
        
        # Calculate megapixels
        megapixels = (width * height) / 1_000_000
        
        if megapixels > max_megapixels:
            return False, f"Image resolution {width}x{height} ({megapixels:.1f}MP) exceeds maximum of {max_megapixels}MP"
        
        return True, f"Image resolution {width}x{height} ({megapixels:.1f}MP) is within limits"
        
    except Exception as e:
        return False, f"Error validating image: {str(e)}"

def resize_image_if_needed(image_url: str, max_megapixels: int = 25) -> tuple[str, str]:
    """
    Resize an image if it exceeds the maximum resolution limit.
    
    Args:
        image_url: URL of the image to resize
        max_megapixels: Maximum allowed megapixels (default 25)
        
    Returns:
        tuple: (resized_image_url, error_message)
    """
    try:
        # Download the image
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Open with PIL
        img = Image.open(BytesIO(response.content))
        width, height = img.size
        
        # Calculate megapixels
        megapixels = (width * height) / 1_000_000
        
        if megapixels <= max_megapixels:
            return image_url, "Image already within size limits"
        
        # Calculate new dimensions to fit within max_megapixels
        ratio = (max_megapixels / megapixels) ** 0.5
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        
        # Resize the image
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save to temporary file
        import tempfile
        import os
        
        # Create a temporary file with .jpg extension
        temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
        os.close(temp_fd)
        
        # Save the resized image
        resized_img.save(temp_path, 'JPEG', quality=85, optimize=True)
        
        # For now, we'll return the original URL with a note about compression
        # In production, you would upload the compressed image to a CDN and return that URL
        print(f"✅ Compressed image from {width}x{height} ({megapixels:.1f}MP) to {new_width}x{new_height} ({max_megapixels}MP)")
        print(f"📁 Compressed image saved to: {temp_path}")
        
        # Return the compressed image path (in production, this would be a CDN URL)
        return temp_path, f"Image compressed from {width}x{height} ({megapixels:.1f}MP) to {new_width}x{new_height} ({max_megapixels}MP)"
        
    except Exception as e:
        return image_url, f"Error processing image: {str(e)}"

def compress_image_url(image_url: str, max_megapixels: int = 25) -> str:
    """
    Compress an image URL if it exceeds the maximum resolution limit.
    Returns the compressed image URL (or original if no compression needed).
    
    Args:
        image_url: URL of the image to compress
        max_megapixels: Maximum allowed megapixels (default 25)
        
    Returns:
        str: Compressed image URL or original URL
    """
    try:
        # Download the image
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Open with PIL
        img = Image.open(BytesIO(response.content))
        width, height = img.size
        
        # Calculate megapixels
        megapixels = (width * height) / 1_000_000
        
        if megapixels <= max_megapixels:
            return image_url  # No compression needed
        
        # Calculate new dimensions to fit within max_megapixels
        ratio = (max_megapixels / megapixels) ** 0.5
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        
        # Resize the image
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save to temporary file
        import tempfile
        import os
        
        # Create a temporary file with .jpg extension
        temp_fd, temp_path = tempfile.mkstemp(suffix='.jpg')
        os.close(temp_fd)
        
        # Save the resized image
        resized_img.save(temp_path, 'JPEG', quality=85, optimize=True)
        
        print(f"✅ Compressed image from {width}x{height} ({megapixels:.1f}MP) to {new_width}x{new_height} ({max_megapixels}MP)")
        
        # For now, return the file path
        # In production, you would upload to a CDN and return the URL
        return temp_path
        
    except Exception as e:
        print(f"❌ Error compressing image: {str(e)}")
        return image_url  # Return original if compression fails

class ListingDatabase:
    """Simple file-based database for listing-ready products with modified images"""
    
    def __init__(self, db_path: str = "listing_ready_products.json"):
        self.db_path = db_path
        self.ensure_db_exists()
    
    def ensure_db_exists(self):
        """Create the database file if it doesn't exist"""
        if not os.path.exists(self.db_path):
            with open(self.db_path, 'w') as f:
                json.dump({}, f)
    
    def load_products(self) -> Dict[str, Any]:
        """Load all products from the database"""
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_products(self, products: Dict[str, Any]):
        """Save products to the database"""
        with open(self.db_path, 'w') as f:
            json.dump(products, f, indent=2)
    
    def add_modified_product(self, sku: str, original_metadata: Dict[str, Any], modified_image_url: str, instruction: str) -> bool:
        """
        Add a product with modified image to the listing database
        
        Args:
            sku: Product SKU
            original_metadata: Original product metadata from search results
            modified_image_url: URL of the modified image
            instruction: The modification instruction used
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate and compress image if needed
            is_valid, validation_msg = validate_image_resolution(modified_image_url)
            if not is_valid:
                print(f"⚠️ Image validation failed for SKU {sku}: {validation_msg}")
                print(f"🔄 Compressing image to meet 25MP limit...")
                # Compress the image
                compressed_image_url = compress_image_url(modified_image_url)
                if compressed_image_url != modified_image_url:
                    print(f"✅ Image compressed successfully for SKU {sku}")
                    modified_image_url = compressed_image_url
                    # Re-validate the compressed image
                    is_valid, validation_msg = validate_image_resolution(modified_image_url)
            
            products = self.load_products()
            
            # Check if product already exists
            if sku in products:
                existing_product = products[sku]
                
                # If product exists, update with new modification
                # Create a list of modifications if it doesn't exist
                if 'modifications' not in existing_product:
                    existing_product['modifications'] = []
                
                # Add new modification to the list
                new_modification = {
                    "modified_image_url": modified_image_url,
                    "instruction": instruction,
                    "modified_at": datetime.now().isoformat(),
                    "image_validation": {
                        "is_valid": is_valid,
                        "message": validation_msg
                    }
                }
                existing_product['modifications'].append(new_modification)
                
                # Update the primary image to be the newest modification
                existing_product['modified_image_url'] = modified_image_url
                existing_product['modification_instruction'] = instruction
                existing_product['modified_at'] = datetime.now().isoformat()
                
                # Rebuild the listing_images with proper ordering:
                # 1. Newest modified image (primary)
                # 2. Previous modifications (newest first)
                # 3. Original images
                listing_images = []
                
                # Add newest modification as primary
                listing_images.append(modified_image_url)
                
                # Add previous modifications (newest first)
                if len(existing_product['modifications']) > 1:
                    # Get all modifications except the current one, sorted by date (newest first)
                    previous_modifications = sorted(
                        existing_product['modifications'][:-1],  # Exclude current
                        key=lambda x: x['modified_at'],
                        reverse=True
                    )
                    for mod in previous_modifications:
                        listing_images.append(mod['modified_image_url'])
                
                # Add original images
                original_images = original_metadata.get('image_urls', [])
                if original_images:
                    listing_images.extend(original_images)
                
                # Update the listing_images structure
                existing_product['listing_images'] = {
                    "primary_image": modified_image_url,
                    "all_images": listing_images,
                    "total_images": len(listing_images)
                }
                
                products[sku] = existing_product
                
            else:
                # Create new product entry
                listing_product = {
                    "sku": sku,
                    "original_metadata": original_metadata,
                    "modified_image_url": modified_image_url,
                    "original_main_image": original_metadata.get('main_image_url', ''),
                    "modification_instruction": instruction,
                    "modified_at": datetime.now().isoformat(),
                    "status": "ready_for_listing",
                    "modifications": [{
                        "modified_image_url": modified_image_url,
                        "instruction": instruction,
                        "modified_at": datetime.now().isoformat(),
                        "image_validation": {
                            "is_valid": is_valid,
                            "message": validation_msg
                        }
                    }],
                    "listing_images": {
                        "primary_image": modified_image_url,
                        "all_images": [modified_image_url] + original_metadata.get('image_urls', []),
                        "total_images": len(original_metadata.get('image_urls', [])) + 1
                    }
                }
                
                products[sku] = listing_product
            
            self.save_products(products)
            print(f"✅ Listing Database: Added/Updated SKU {sku} with modified image")
            if not is_valid:
                print(f"⚠️ Warning: Image may cause Shopify upload issues due to size")
            return True
            
        except Exception as e:
            print(f"❌ Listing Database: Error adding product {sku}: {str(e)}")
            return False
    
    def get_product(self, sku: str) -> Dict[str, Any]:
        """Get a product from the listing database"""
        products = self.load_products()
        return products.get(sku, {})
    
    def list_products(self) -> List[str]:
        """List all SKUs in the listing database"""
        products = self.load_products()
        return list(products.keys())
    
    def remove_product(self, sku: str) -> bool:
        """Remove a product from the listing database"""
        try:
            products = self.load_products()
            if sku in products:
                del products[sku]
                self.save_products(products)
                print(f"✅ Listing Database: Removed SKU {sku}")
                return True
            return False
        except Exception as e:
            print(f"❌ Listing Database: Error removing product {sku}: {str(e)}")
            return False
    
    def add_product_from_search(self, sku: str, metadata: Dict[str, Any]) -> bool:
        """
        Add a product from search results to the listing database (without modifications)
        
        Args:
            sku: Product SKU
            metadata: Product metadata from search results
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            products = self.load_products()
            
            # Check if product already exists
            if sku in products:
                print(f"ℹ️ Listing Database: SKU {sku} already exists in database")
                return True
            
            # Create the listing-ready product entry (without modifications)
            listing_product = {
                "sku": sku,
                "original_metadata": metadata,
                "modified_image_url": None,  # No modifications
                "original_main_image": metadata.get('main_image_url', ''),
                "modification_instruction": None,  # No modifications
                "added_at": datetime.now().isoformat(),
                "status": "ready_for_listing",
                "listing_images": {
                    "primary_image": metadata.get('main_image_url', ''),
                    "additional_images": metadata.get('image_urls', []),
                    "total_images": len(metadata.get('image_urls', []))
                }
            }
            
            # Add to database
            products[sku] = listing_product
            self.save_products(products)
            
            print(f"✅ Listing Database: Added SKU {sku} from search results (no modifications)")
            return True
            
        except Exception as e:
            print(f"❌ Listing Database: Error adding product {sku}: {str(e)}")
            return False
    
    def add_multiple_products_from_search(self, search_results: List[Dict]) -> List[str]:
        """
        Add multiple products from search results to the listing database
        
        Args:
            search_results: List of search result dictionaries
            
        Returns:
            List[str]: List of successfully added SKUs
        """
        added_skus = []
        for result in search_results:
            metadata = result.get('metadata', {})
            sku = metadata.get('sku')
            if sku:
                if self.add_product_from_search(sku, metadata):
                    added_skus.append(sku)
        
        return added_skus

def parse_confirmation_intent(user_query: str) -> tuple:
    """
    Use LLM to classify the user's confirmation response after image modification.
    Returns a tuple: (intent, followup_instruction)
    """
    print(f"🔍 Debug - parse_confirmation_intent:")
    print(f"   Input user_query: '{user_query}'")
    print(f"   Input type: {type(user_query)}")
    print(f"   Input length: {len(user_query)}")
    
    prompt = f"""
You are an expert at understanding user intent in product listing workflows. 

**CRITICAL: Analyze ONLY the user's current response below. Do NOT consider any previous conversation context.**

CONTEXT: The user has just been shown a modified product image and is responding to whether they want to add it to the listing database.

USER'S CURRENT RESPONSE: "{user_query}"

ANALYZE ONLY this response and classify their intent:

**add_only**: User wants to add the modified image to the database but NOT list yet
- Examples: "yes", "perfect", "looks good", "ok", "sure", "好的", "可以", "不错", "great", "nice", "awesome"

**add_and_list**: User wants to add the modified image AND immediately list the product on Shopify
- Examples: "yes and list", "add and publish", "list this", "put it on shopify", "publish it", "上架", "发布", "现在上架", "list this product", "now list this", "this is great! now list this product on shopify", "perfect, list it", "ok, publish it", "sure good enough now put it on shopify", "yes, now list it", "add it and list", "list it now", "publish to shopify", "上架到shopify", "let's list it", "go ahead and publish", "make it live", "这个ok，把这款产品上架到shopify"

**skip_and_list**: User does NOT want to add the modified image, but wants to list the product (with original image)
- Examples: "no, but list it", "skip image, just list", "list without modification", "list the original", "不用修改，直接上架", "don't use the modified image, but list it"

**skip**: User does NOT want to add the modified image and does NOT want to list
- Examples: "no", "discard", "don't use", "not good", "不好", "不要", "算了", "cancel", "never mind"

**clarify**: The intent is truly unclear or ambiguous
- Examples: "maybe", "I don't know", "what do you think?", unclear responses

**FOLLOW-UP INSTRUCTION**: If the user also requests another image modification (e.g., "generate another one of the same product in an outdoor vineyard"), extract the follow-up instruction as a string. If not, return null.

**ANALYSIS RULES:**
1. **Focus ONLY on the current response** - ignore any previous conversation
2. **Look for positive words** - "ok", "good", "perfect", "可以", "不错" indicate satisfaction
3. **Look for listing keywords** - "list", "publish", "上架", "shopify" indicate listing intent
4. **Chinese responses** - "这个ok，把这款产品上架到shopify" = add_and_list (satisfied + wants to list)
5. **Combination responses** - If user is satisfied AND wants to list = add_and_list
6. **If the user also requests another image modification, extract the follow-up instruction.**

**STEP-BY-STEP ANALYSIS:**
1. Is the user satisfied with the image? (yes/no/ambiguous)
2. Does the user want to list/publish the product? (yes/no/ambiguous)
3. Does the user request another image modification? (yes/no, if yes, extract the instruction)
4. Based on answers, classify the intent and extract follow-up instruction.

Respond with a JSON object:
{{"intent": "intent_type", "reasoning": "Detailed explanation of how you interpreted the user's response", "followup_instruction": "the follow-up image modification instruction, or null if none"}}
"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
    response = llm.invoke(prompt)
    try:
        content = response.content.strip()
        if content.startswith('```'):
            import re
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                content = match.group(0)
        result = json.loads(content)
        intent = result.get("intent", "clarify")
        reasoning = result.get("reasoning", "")
        followup_instruction = result.get("followup_instruction", None)
        print(f"🤖 Intent parsing reasoning: {reasoning}")
        print(f"🤖 Follow-up instruction: {followup_instruction}")
        return intent, followup_instruction
    except Exception as e:
        print(f"❌ Error in intent parsing: {e}")
        return "clarify", None

def listing_database_node(state):
    """
    LangGraph node for handling listing database operations
    
    Expects state to contain:
    - messages: List of messages (to extract user_query from last message)
    - modified_images: List of modified image results
    - search_results: List of products (for context)
    - awaiting_confirmation: Boolean indicating if waiting for confirmation
    
    Returns state with:
    - listing_database_response: Response about database operation
    - listing_ready_products: Updated list of ready products
    """
    print("🔄 LangGraph: Executing 'listing_database' node...")
    
    # Initialize the database
    db = ListingDatabase()
    
    # Extract user query from the last message (same as planning node)
    last_message = state["messages"][-1]
    user_query = extract_text_from_multimodal_content(last_message.content)
    
    # Get state information
    modified_images = state.get("modified_images", [])
    search_results = state.get("search_results", [])
    awaiting_confirmation = state.get("awaiting_confirmation", False)
    
    # LLM-based intent parsing for confirmation
    if awaiting_confirmation:
        print(f"🔍 Debug - Listing Database Node:")
        print(f"   user_query: '{user_query}'")
        print(f"   user_query type: {type(user_query)}")
        print(f"   user_query length: {len(user_query)}")
        print(f"   awaiting_confirmation: {awaiting_confirmation}")
        intent, followup_instruction = parse_confirmation_intent(user_query)
        print(f"🤖 Confirmation intent: {intent}")
        response_text = None
        ready_skus = db.list_products()
        sku = None
        if modified_images:
            modification_result = modified_images[0]
            sku = modification_result.get('sku')
        # --- Existing intent handling logic ---
        if intent == "add_only":
            # Add to DB, prompt for next action
            if modified_images:
                if sku and modification_result.get('status') == 'success':
                    original_metadata = None
                    for product in search_results:
                        if product.get('metadata', {}).get('sku') == sku:
                            original_metadata = product.get('metadata', {})
                            break
                    if original_metadata:
                        success = db.add_modified_product(
                            sku=sku,
                            original_metadata=original_metadata,
                            modified_image_url=modification_result['modified_url'],
                            instruction=modification_result['instruction']
                        )
                        if success:
                            response_text = f"""✅ **Successfully Added to Listing Database!**\n\n**SKU {sku}** has been added to the listing preparation database with the modified image.\n\n**What happens next:**\n- The modified image is now set as the primary image for this product\n- All original images are preserved as additional views\n- This product is ready for Shopify listing with the new background\n- You can now use commands like \"list this on Shopify\" or \"publish to Shopify\"\n\n**Modified Image:** {modification_result['modified_url']}\n\nWould you like to:\n- **List this product on Shopify now**\n- **Modify another product's image**\n- **View all listing-ready products**"""
                        else:
                            response_text = f"""❌ **Database Error**\n\nSorry, I couldn't add SKU {sku} to the listing database. Please try again."""
                    else:
                        response_text = f"""❌ **Product Not Found**\n\nCouldn't find the original product data for SKU {sku}. Please try the image modification again."""
                else:
                    response_text = """❌ **No Valid Modification**\n\nNo successful image modification found to add to the database."""
            else:
                response_text = """❌ **No Modified Images**\n\nNo modified images found to add to the database."""
            ready_skus = db.list_products()
        elif intent == "add_and_list":
            # Add to DB, then trigger Shopify agent
            if modified_images:
                if sku and modification_result.get('status') == 'success':
                    original_metadata = None
                    for product in search_results:
                        if product.get('metadata', {}).get('sku') == sku:
                            original_metadata = product.get('metadata', {})
                            break
                    if original_metadata:
                        db.add_modified_product(
                            sku=sku,
                            original_metadata=original_metadata,
                            modified_image_url=modification_result['modified_url'],
                            instruction=modification_result['instruction']
                        )
            ready_skus = db.list_products()
            # Set a flag or action to trigger Shopify agent in the workflow
            state["action_type"] = "shopify_agent"
            response_text = ""
        elif intent == "skip_and_list":
            # Do not add, trigger Shopify agent
            ready_skus = db.list_products()
            state["action_type"] = "shopify_agent"
            response_text = ""
        elif intent == "skip":
            # Do not add, prompt for next action
            response_text = """❌ **Modification Discarded**\n\nThe image modification has been discarded. The original product images remain unchanged.\n\nYou can:\n- **Try a different modification** with a new instruction\n- **Search for other products** to modify\n- **List the original product** on Shopify"""
            ready_skus = db.list_products()
        else:
            # Clarify
            response_text = """🤔 **I'm not sure what you'd like to do**\n\nIf you've just modified an image, please respond with:\n- **\"Yes\"** to add it to the listing database\n- **\"No\"** to discard the modification\n- **\"Yes and list this\"** to add and list\n- **\"No, but go ahead and list\"** to skip adding and list\n\nOr you can:\n- **\"View all listing-ready products\"** to see what's ready\n- **\"Remove SKU\"** to remove a product from the database"""
            ready_skus = db.list_products()
        # --- Always trigger follow-up if present ---
        if followup_instruction and isinstance(followup_instruction, str) and followup_instruction.strip():
            print(f"🔄 Detected follow-up image modification instruction: {followup_instruction}")
            # Use the same SKU as the last modified product if available
            state["image_modification_request"] = {
                "instruction": followup_instruction,
                "sku": sku
            }
            state["plan_action"] = "image_agent"
        # Always append a new AIMessage for every user action
        messages = state.get("messages", [])
        if response_text:
            messages = messages + [AIMessage(content=response_text)]
        return {**state, "listing_database_response": response_text, "listing_ready_products": ready_skus, "awaiting_confirmation": False, "messages": messages}
    
    elif "view all listing" in user_query or "show listing" in user_query or "list ready" in user_query:
        # User wants to see all listing-ready products
        ready_skus = db.list_products()
        if ready_skus:
            response_text = f"""📋 **Listing-Ready Products**

Found **{len(ready_skus)}** products ready for Shopify listing:

"""
            for i, sku in enumerate(ready_skus, 1):
                product_data = db.get_product(sku)
                modified_at = product_data.get('modified_at', 'Unknown')
                instruction = product_data.get('modification_instruction', 'Unknown')
                response_text += f"{i}. **SKU: {sku}**\n"
                response_text += f"   Modified: {modified_at[:10]}\n"
                response_text += f"   Instruction: {instruction}\n\n"
            
            response_text += "**Commands you can use:**\n"
            response_text += "- **'List all on Shopify'** - Publish all ready products\n"
            response_text += "- **'List SKU on Shopify'** - Publish specific product\n"
            response_text += "- **'Remove SKU'** - Remove from listing database"
        else:
            response_text = """📋 **No Listing-Ready Products**

No products are currently in the listing preparation database.

To add products:
1. Search for products you want to modify
2. Request image modifications
3. Confirm to add them to the listing database"""
    
    elif "remove" in user_query and any(sku in user_query.upper() for sku in db.list_products()):
        # User wants to remove a product from listing database
        for sku in db.list_products():
            if sku.lower() in user_query.lower():
                success = db.remove_product(sku)
                if success:
                    response_text = f"""✅ **Removed SKU {sku}**

SKU {sku} has been removed from the listing preparation database."""
                else:
                    response_text = f"""❌ **Failed to Remove SKU {sku}**

There was an error removing the product from the database."""
                break
        else:
            response_text = """❌ **SKU Not Found**

Couldn't find the specified SKU in the listing database."""
    
    else:
        # Default response
        response_text = """🤔 **I'm not sure what you'd like to do**

If you've just modified an image, please respond with:
- **"Yes"** to add it to the listing database
- **"No"** to discard the modification

Or you can:
- **"View all listing-ready products"** to see what's ready
- **"Remove SKU"** to remove a product from the database"""
    
    # Get current listing-ready products for context
    ready_skus = db.list_products()
    
    return {
        **state,
        "listing_database_response": response_text,
        "listing_ready_products": ready_skus,
        "awaiting_confirmation": False  # Reset confirmation status
    } 