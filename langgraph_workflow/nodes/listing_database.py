import json
import os
from typing import Dict, List, Any
from datetime import datetime

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
            products = self.load_products()
            
            # Create the listing-ready product entry
            listing_product = {
                "sku": sku,
                "original_metadata": original_metadata,
                "modified_image_url": modified_image_url,
                "original_main_image": original_metadata.get('main_image_url', ''),
                "modification_instruction": instruction,
                "modified_at": datetime.now().isoformat(),
                "status": "ready_for_listing",
                "listing_images": {
                    "primary_image": modified_image_url,
                    "additional_images": original_metadata.get('image_urls', []),
                    "total_images": len(original_metadata.get('image_urls', [])) + 1
                }
            }
            
            # Add to database
            products[sku] = listing_product
            self.save_products(products)
            
            print(f"✅ Listing Database: Added SKU {sku} with modified image")
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

def listing_database_node(state):
    """
    LangGraph node for handling listing database operations
    
    Expects state to contain:
    - user_query: Current user query
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
    
    # Get state information
    user_query = state.get("user_query", "").lower()
    modified_images = state.get("modified_images", [])
    search_results = state.get("search_results", [])
    awaiting_confirmation = state.get("awaiting_confirmation", False)
    
    # Check if user is confirming to add modified image to database
    confirmation_keywords = ["yes", "yes, incorporate it", "incorporate", "add it", "save it", "use it"]
    rejection_keywords = ["no", "no, keep original", "discard", "don't use", "keep original"]
    
    if awaiting_confirmation and any(keyword in user_query for keyword in confirmation_keywords):
        # User confirmed - add to listing database
        if modified_images:
            modification_result = modified_images[0]
            sku = modification_result.get('sku')
            
            if sku and modification_result.get('status') == 'success':
                # Find the original product metadata
                original_metadata = None
                for product in search_results:
                    if product.get('metadata', {}).get('sku') == sku:
                        original_metadata = product.get('metadata', {})
                        break
                
                if original_metadata:
                    success = db.add_modified_product(
                        sku=sku,
                        original_metadata=original_metadata,
                        modified_image_url=modification_result['modified_image_url'],
                        instruction=modification_result['instruction']
                    )
                    
                    if success:
                        response_text = f"""✅ **Successfully Added to Listing Database!**

**SKU {sku}** has been added to the listing preparation database with the modified image.

**What happens next:**
- The modified image is now set as the primary image for this product
- All original images are preserved as additional views
- This product is ready for Shopify listing with the new background
- You can now use commands like "list this on Shopify" or "publish to Shopify"

**Modified Image:** {modification_result['modified_image_url']}

Would you like to:
- **List this product on Shopify now**
- **Modify another product's image**
- **View all listing-ready products**"""
                    else:
                        response_text = f"""❌ **Database Error**

Sorry, I couldn't add SKU {sku} to the listing database. Please try again."""
                else:
                    response_text = f"""❌ **Product Not Found**

Couldn't find the original product data for SKU {sku}. Please try the image modification again."""
            else:
                response_text = """❌ **No Valid Modification**

No successful image modification found to add to the database."""
        else:
            response_text = """❌ **No Modified Images**

No modified images found to add to the database."""
    
    elif awaiting_confirmation and any(keyword in user_query for keyword in rejection_keywords):
        # User rejected - discard the modification
        response_text = """❌ **Modification Discarded**

The image modification has been discarded. The original product images remain unchanged.

You can:
- **Try a different modification** with a new instruction
- **Search for other products** to modify
- **List the original product** on Shopify"""
    
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