from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_models import ChatOpenAI
import json
from typing import Dict, List, Any, Optional

class ProductSelectionIntentParser:
    """
    A unified intent parser for product selection used by both Image Agent and Shopify Agent.
    Determines which products the user is referring to based on their natural language query.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
    
    def parse_product_selection(self, 
                              user_query: str, 
                              available_products: List[Dict], 
                              conversation_context: str = "") -> Dict[str, Any]:
        """
        Parse user intent to determine which products they want to work with.
        
        Args:
            user_query: Current user query
            available_products: List of product dictionaries with metadata
            conversation_context: Previous conversation messages for context
            
        Returns:
            Dict containing:
            - selected_products: List of selected product dictionaries
            - selected_skus: List of selected SKUs
            - reasoning: Explanation of the selection
            - confidence: Confidence score (0-1)
        """
        
        if not available_products:
            return {
                "selected_products": [],
                "selected_skus": [],
                "reasoning": "No products available",
                "confidence": 0.0
            }
        
        # Build product list for LLM analysis
        product_list = []
        for i, product in enumerate(available_products, 1):
            metadata = product.get('metadata', {})
            sku = metadata.get('sku', '')
            
            # Create descriptive name
            name_parts = []
            if metadata.get('category'):
                name_parts.append(metadata.get('category'))
            if metadata.get('material'):
                name_parts.append(metadata.get('material'))
            if metadata.get('color'):
                name_parts.append(metadata.get('color'))
            
            descriptive_name = " ".join(name_parts) if name_parts else f"Product {i}"
            
            product_info = f"{i}. SKU: {sku}, Name: {descriptive_name}"
            if metadata.get('weight'):
                product_info += f", Weight: {metadata.get('weight')} lbs"
            if metadata.get('characteristics_text'):
                chars = metadata.get('characteristics_text', '')[:100]
                product_info += f", Features: {chars}..."
            
            product_list.append(product_info)
        
        product_list_text = "\n".join(product_list)
        
        # Build conversation context
        conversation_parts = []
        for msg in conversation_context.split('\n')[-10:]:  # Last 10 messages
            if msg.strip():
                conversation_parts.append(msg)
        
        conversation_text = "\n".join(conversation_parts)
        
        prompt = f"""You are an expert at understanding user intent for product selection. Analyze the user's natural language request and determine which specific products they want to work with.

CONVERSATION CONTEXT:
{conversation_text}

AVAILABLE PRODUCTS:
{product_list_text}

USER'S CURRENT QUERY:
{user_query}

TASK: Understand the user's intent and select the appropriate products.

CRITICAL INSTRUCTIONS:
1. **PRIORITIZE CURRENT QUERY**: The current user query is the most important source of intent. If the user provides specific product details in their current query, use those details to identify the product, regardless of conversation context.
2. **EXACT CHARACTERISTIC MATCHING**: When the user mentions specific product characteristics (color, material, category, weight, dimensions), find products that match ALL mentioned characteristics exactly.
3. **IGNORE AMBIGUOUS CONTEXT**: If the conversation context contains general requests like "find chairs" but the current query specifies a particular product, focus on the current query.

ANALYSIS APPROACH:
1. **Extract specific characteristics** from the current query (color, material, category, weight, dimensions, SKU)
2. **Find exact matches** for ALL mentioned characteristics
3. **Prioritize specific over general** - specific product details override general category requests
4. **Consider conversation context** only when current query is ambiguous

PRODUCT REFERENCE PATTERNS:
- **Direct SKU mention**: "W2103P277202", "SKU W1880115228"
- **Characteristic matching**: "white plastic chair", "yellow linen", "39.6 lbs"
- **Positional reference**: "the first one", "this product", "that chair"
- **Contextual reference**: "the one we just discussed", "the chair I liked"
- **Category reference**: "all chairs", "every table", "chairs only"

SELECTION LOGIC (in order of priority):
1. **Exact characteristic match**: If user mentions specific attributes, find products matching ALL mentioned characteristics
2. **Exact SKU match**: If user mentions a specific SKU, select only that product
3. **Recent context**: If user refers to recently discussed products, prioritize those
4. **Category match**: If user mentions a product type, select all products of that type
5. **Default behavior**: Only select all products if user explicitly requests everything

EXAMPLES OF USER INTENTS:
- "list it on shopify Category: Patio Seating Color: White Material: Plastic Weight: 39.6 lbs" → Select white plastic patio seating weighing 39.6 lbs
- "modify the black hdpe chair" → Select black HDPE chairs only
- "change this product's image" → Select most recently discussed product
- "edit all chairs" → Select all chair products
- "上架黑椅子" → Select black chairs only
- "modify the yellow one" → Select yellow products only
- "work with everything" → Select all products

IMPORTANT: If the user provides specific product characteristics in their current query, use those to find the exact product, even if the conversation context suggests a different intent.

Return a JSON response with:
{{
    "selected_skus": ["SKU1", "SKU2", ...],
    "reasoning": "Detailed explanation of how you interpreted the user's intent and why these specific products were selected",
    "confidence": 0.95
}}

If you cannot determine specific products, return an empty array for selected_skus and explain why.

Response:"""

        response = self.llm.invoke(prompt)
        response_content = response.content.strip()
        
        try:
            # Handle markdown-wrapped JSON
            if response_content.startswith('```'):
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_content, re.DOTALL)
                if json_match:
                    response_content = json_match.group(1)
                else:
                    json_match = re.search(r'\{.*?\}', response_content, re.DOTALL)
                    if json_match:
                        response_content = json_match.group(0)
            
            result = json.loads(response_content)
        except json.JSONDecodeError:
            print(f"❌ JSON parsing failed in product selection: {response_content}")
            # Fallback: try to extract SKUs from text
            import re
            sku_matches = re.findall(r'\b[A-Z]{2}\d+[A-Z]*\b', response_content)
            valid_skus = [sku for sku in sku_matches if len(sku) >= 8 and any(char.isdigit() for char in sku)]
            if valid_skus:
                result = {"selected_skus": valid_skus, "reasoning": "Extracted from text response", "confidence": 0.5}
            else:
                result = {"selected_skus": [], "reasoning": "JSON parsing failed", "confidence": 0.0}
        
        selected_skus = result.get("selected_skus", [])
        reasoning = result.get("reasoning", "")
        confidence = result.get("confidence", 0.0)
        
        # Filter products based on selected SKUs
        selected_products = []
        for product in available_products:
            sku = product.get('metadata', {}).get('sku', '')
            if sku in selected_skus:
                selected_products.append(product)
        
        # Fallback: If LLM didn't select any products but user provided specific characteristics,
        # try direct characteristic matching
        if not selected_products and confidence < 0.7:
            print("🔄 Fallback: Attempting direct characteristic matching...")
            fallback_products = self._direct_characteristic_matching(user_query, available_products)
            if fallback_products:
                selected_products = fallback_products
                selected_skus = [p.get('metadata', {}).get('sku', '') for p in fallback_products]
                reasoning = f"Fallback characteristic matching: {reasoning}"
                confidence = 0.8
        
        return {
            "selected_products": selected_products,
            "selected_skus": selected_skus,
            "reasoning": reasoning,
            "confidence": confidence
        }
    
    def _direct_characteristic_matching(self, user_query: str, available_products: List[Dict]) -> List[Dict]:
        """
        Direct characteristic matching as a fallback when LLM selection fails.
        """
        import re
        
        # Extract characteristics from user query
        characteristics = {}
        
        # Extract color
        color_match = re.search(r'color:\s*(\w+)', user_query, re.IGNORECASE)
        if color_match:
            characteristics['color'] = color_match.group(1).lower()
        
        # Extract material
        material_match = re.search(r'material:\s*(\w+)', user_query, re.IGNORECASE)
        if material_match:
            characteristics['material'] = material_match.group(1).lower()
        
        # Extract category
        category_match = re.search(r'category:\s*([^,\n]+)', user_query, re.IGNORECASE)
        if category_match:
            characteristics['category'] = category_match.group(1).strip().lower()
        
        # Extract weight
        weight_match = re.search(r'weight:\s*([\d.]+)', user_query, re.IGNORECASE)
        if weight_match:
            characteristics['weight'] = float(weight_match.group(1))
        
        # Extract SKU
        sku_match = re.search(r'sku:\s*([A-Z0-9]+)', user_query, re.IGNORECASE)
        if sku_match:
            characteristics['sku'] = sku_match.group(1)
        
        if not characteristics:
            return []
        
        print(f"🔍 Direct matching characteristics: {characteristics}")
        
        # Find products matching ALL characteristics
        matching_products = []
        for product in available_products:
            metadata = product.get('metadata', {})
            matches_all = True
            
            for char_type, char_value in characteristics.items():
                if char_type == 'sku':
                    if metadata.get('sku', '').lower() != char_value.lower():
                        matches_all = False
                        break
                elif char_type == 'weight':
                    product_weight = metadata.get('weight')
                    if product_weight is None or abs(float(product_weight) - char_value) > 0.1:
                        matches_all = False
                        break
                else:
                    product_value = metadata.get(char_type, '').lower()
                    if char_value.lower() not in product_value:
                        matches_all = False
                        break
            
            if matches_all:
                matching_products.append(product)
        
        print(f"🔍 Direct matching found {len(matching_products)} products")
        return matching_products

# Global instance for reuse
product_selection_parser = ProductSelectionIntentParser()

def intent_parser_node(state):
    """
    LangGraph node for parsing user intent and mapping to products.
    
    Expects state to contain:
    - user_query: Current user query
    - search_results: List of available products
    - messages: Conversation history
    - action_type: Type of action being performed
    
    Returns state with:
    - parsed_intent: Dict with selected products and reasoning
    """
    print("🔄 LangGraph: Executing 'intent_parser' node...")
    
    # Initialize the intent parser
    parser = ProductSelectionIntentParser()
    
    # Get inputs from state
    user_query = state.get("user_query", "")
    search_results = state.get("search_results", [])
    messages = state.get("messages", [])
    action_type = state.get("action_type", "general")
    
    # Build conversation context first
    conversation_context = ""
    for message in messages[:-1]:  # Exclude current message
        if hasattr(message, 'content'):
            # Better role detection
            if isinstance(message, HumanMessage):
                role = "User"
            elif isinstance(message, AIMessage):
                role = "Assistant"
            else:
                # Fallback to type attribute
                role = "User" if hasattr(message, 'type') and message.type == "human" else "Assistant"
            conversation_context += f"{role}: {message.content}\n"
    
    # Extract products from conversation context if search_results is empty
    if not search_results and conversation_context:
        print("🔍 Intent Parser: No search_results, extracting products from conversation context...")
        
        # Look for SKUs in the conversation context
        import re
        sku_pattern = r'SKU:\s*([A-Z0-9]+)'
        found_skus = re.findall(sku_pattern, conversation_context)
        
        if found_skus:
            print(f"🔍 Intent Parser: Found SKUs in conversation: {found_skus}")
            # Create a minimal product structure for the found SKUs
            extracted_products = []
            for i, sku in enumerate(found_skus):
                extracted_products.append({
                    'metadata': {
                        'sku': sku,
                        'name': f'Product {sku}',
                        'category': 'Unknown',
                        'material': 'Unknown',
                        'color': 'Unknown'
                    }
                })
            
            # Use extracted products as search_results
            search_results = extracted_products
            print(f"🔍 Intent Parser: Created {len(extracted_products)} products from conversation context")
    
    if not search_results:
        return {
            **state,
            "parsed_intent": {
                "selected_products": [],
                "selected_skus": [],
                "reasoning": "No products available to select from",
                "confidence": 0.0
            }
        }
    
    # Parse intent
    parsed_intent = parser.parse_product_selection(
        user_query=user_query,
        available_products=search_results,
        conversation_context=conversation_context
    )
    
    print(f"🔍 Intent Parser: {parsed_intent['reasoning']}")
    print(f"🎯 Selected SKUs: {parsed_intent['selected_skus']}")
    print(f"📊 Confidence: {parsed_intent['confidence']}")
    
    return {
        **state,
        "parsed_intent": parsed_intent
    } 