#!/usr/bin/env python3
"""
Test script for new SKU WF288172AAP
"""

from tools.giga_api import GigaApiClient
import json

def test_new_sku():
    """Test the new SKU WF288172AAP"""
    print("🧪 Testing new SKU: WF288172AAP")
    
    # Initialize client
    client = GigaApiClient()
    
    # Test SKU
    test_sku = "W1658P191740"
    site = "US"
    
    try:
        print(f"📦 Requesting product: {test_sku} from site: {site}")
        
        # Get products
        products = client.get_products_by_skus(site, [test_sku])
        
        if products:
            product = products[0]
            
            print(f"✅ Success! Retrieved product")
            print(f"   SKU: {product.sku}")
            print(f"   Name: {product.name}")
            print(f"   Category: {product.category}")
            print(f"   Description: {product.description}")
            print(f"   Weight: {product.weight} {product.weight_unit if hasattr(product, 'weight_unit') else 'lb'}")
            print(f"   Dimensions: {product.length} x {product.width} x {product.height} {product.length_unit if hasattr(product, 'length_unit') else 'in'}")
            
            # Check if product has meaningful data
            has_data = (
                product.name is not None or
                product.description is not None or
                product.category is not None or
                (product.attributes and any([
                    product.attributes.main_color,
                    product.attributes.scene,
                    product.attributes.main_material
                ]))
            )
            
            print(f"\n📊 Data Analysis:")
            print(f"   Has populated data: {has_data}")
            
            if has_data:
                print(f"   🎉 POPULATED DATA FOUND!")
                
                if product.attributes:
                    print(f"   Attributes:")
                    print(f"     Color: {product.attributes.main_color}")
                    print(f"     Scene: {product.attributes.scene}")
                    print(f"     Material: {product.attributes.main_material}")
                
                if product.combo_info:
                    print(f"   Combo Info:")
                    for i, combo in enumerate(product.combo_info):
                        print(f"     {i+1}. Length: {combo.length}, Width: {combo.width}, Height: {combo.height}, Weight: {combo.weight}")
            else:
                print(f"   📭 Empty product data (same as other SKUs)")
            
            # Save to file
            with open("new_sku_test.json", "w") as f:
                json.dump(product.__dict__, f, indent=2, default=str)
            print(f"\n💾 Product data saved to new_sku_test.json")
            
        else:
            print(f"❌ No product found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_multiple_skus():
    print("🧪 Testing multiple SKUs")
    client = GigaApiClient()
    sku_list = [
        "W1885P263555","GS008004AAA","GS000086AAA","W1885P272259","W24172223","W24183624",
        "W87470711","W2103P277202","W2103P277201","W2831P241976","W3204P300597","W142763539",
        "W2831P313087","W2831P313981","W3150P280546","W1767P195862","W2640P257528","N717P221495F",
        "WF285323AAA","WF285323AAF","W1885S00012","W3163S00019"
    ]
    site = "US"
    try:
        print(f"📦 Requesting products: {sku_list} from site: {site}")
        products = client.get_products_by_skus(site, sku_list)
        if products:
            all_products = []
            for product in products:
                print(f"✅ Success! Retrieved product {product.sku}")
                prod_dict = product.__dict__
                prod_dict["US"] = True
                all_products.append(prod_dict)
            with open("all_new_skus_us.json", "w") as f:
                json.dump(all_products, f, indent=2, default=str)
            print(f"💾 All product data saved to all_new_skus_us.json")
        else:
            print("❌ No products found")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multiple_skus() 