from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_models import ChatOpenAI
import json
from typing import Dict, List, Any, Optional, Tuple

class IntentParserAgent:
    """
    A reusable agent that parses user intent and maps ordinal references to specific products.
    Can be used by both image agent and Shopify agent for consistent product selection.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
    
    def parse_intent(self, 
                    user_query: str, 
                    available_products: List[Dict], 
                    conversation_context: str = "",
                    action_type: str = "general") -> Dict[str, Any]:
        """
        Parse user intent and map ordinal references to specific products.
        
        Args:
            user_query: Current user query
            available_products: List of product dictionaries with metadata
            conversation_context: Previous conversation messages
            action_type: Type of action ("image_modification", "shopify_listing", "general")
            
        Returns:
            Dict containing:
            - selected_products: List of selected product dictionaries
            - selected_skus: List of selected SKUs
            - reasoning: Explanation of the selection
            - language: Detected language
            - confidence: Confidence score (0-1)
        """
        
        if not available_products:
            return {
                "selected_products": [],
                "selected_skus": [],
                "reasoning": "No products available",
                "language": "en",
                "confidence": 0.0
            }
        
        # Extract SKUs and create product mapping
        product_mapping = {}
        available_skus = []
        
        for i, product in enumerate(available_products):
            metadata = product.get('metadata', {})
            sku = metadata.get('sku', '')
            if sku:
                product_mapping[sku] = {
                    'product': product,
                    'index': i + 1,
                    'sku': sku,
                    'category': metadata.get('category', ''),
                    'material': metadata.get('material', ''),
                    'color': metadata.get('color', '')
                }
                available_skus.append(sku)
        
        # Build analysis prompt based on action type
        if action_type == "image_modification":
            action_context = "modify images for"
            instruction_hint = "Look for image modification requests and which products they want to modify"
        elif action_type == "shopify_listing":
            action_context = "list on Shopify"
            instruction_hint = "Look for products they want to list on Shopify"
        else:
            action_context = "work with"
            instruction_hint = "Look for any product-related requests"
        
        analysis_prompt = f"""
You are an intent parsing agent that helps determine which products a user wants to {action_context}.

CONVERSATION HISTORY:
{conversation_context}

CURRENT USER QUERY:
{user_query}

AVAILABLE PRODUCTS:
{json.dumps([{
    'index': i + 1,
    'sku': mapping['sku'],
    'category': mapping['category'],
    'material': mapping['material'],
    'color': mapping['color']
} for i, mapping in enumerate(product_mapping.values())], indent=2)}

TASK: {instruction_hint}.

Look for:
1. Ordinal references: "first one", "second product", "the third", "1st", "2nd", etc.
2. Specific product mentions: "the wooden chair", "the blue table", etc.
3. Quantity references: "both", "all three", "these two", etc.
4. SKU references: direct SKU mentions
5. Contextual references: "the one we discussed", "that product", etc.

IMPORTANT: When mapping ordinal references, use the order shown in the AVAILABLE PRODUCTS list above.
- "first one" = index 1
- "second one" = index 2
- etc.

Return a JSON object:
{{
    "selected_indices": [1, 2, ...],  // Product indices from the list above
    "selected_skus": ["SKU1", "SKU2", ...],
    "reasoning": "explanation of your decision",
    "language": "en" or "zh-cn",
    "confidence": 0.95,  // 0-1 confidence score
    "detected_ordinals": ["first", "second", ...],  // Any ordinal terms found
    "detected_quantities": ["both", "all", ...]  // Any quantity terms found
}}

If no specific products mentioned, return empty arrays for selected_indices and selected_skus.
Language detection: Only support "zh-cn" for Chinese or "en" for English.

Return ONLY valid JSON.
"""
        
        try:
            analysis_response = self.llm.invoke(analysis_prompt)
            content = analysis_response.content.strip()
            
            # Clean up JSON response
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            analysis_result = json.loads(content)
            
            # Map indices back to products
            selected_products = []
            selected_skus = analysis_result.get("selected_skus", [])
            
            # If we have indices, use those to get products
            selected_indices = analysis_result.get("selected_indices", [])
            if selected_indices:
                for idx in selected_indices:
                    if 1 <= idx <= len(available_products):
                        selected_products.append(available_products[idx - 1])
            
            # If we have SKUs but no indices, use SKUs to get products
            elif selected_skus:
                for sku in selected_skus:
                    if sku in product_mapping:
                        selected_products.append(product_mapping[sku]['product'])
            
            return {
                "selected_products": selected_products,
                "selected_skus": selected_skus,
                "reasoning": analysis_result.get("reasoning", ""),
                "language": analysis_result.get("language", "en"),
                "confidence": analysis_result.get("confidence", 0.0),
                "detected_ordinals": analysis_result.get("detected_ordinals", []),
                "detected_quantities": analysis_result.get("detected_quantities", [])
            }
            
        except Exception as e:
            print(f"⚠️ Intent parsing failed: {e}")
            return {
                "selected_products": [],
                "selected_skus": [],
                "reasoning": f"Error parsing intent: {str(e)}",
                "language": "en",
                "confidence": 0.0,
                "detected_ordinals": [],
                "detected_quantities": []
            }

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
    parser = IntentParserAgent()
    
    # Get inputs from state
    user_query = state.get("user_query", "")
    search_results = state.get("search_results", [])
    messages = state.get("messages", [])
    action_type = state.get("action_type", "general")
    
    if not search_results:
        return {
            **state,
            "parsed_intent": {
                "selected_products": [],
                "selected_skus": [],
                "reasoning": "No products available to select from",
                "language": "en",
                "confidence": 0.0
            }
        }
    
    # Build conversation context
    conversation_context = ""
    for message in messages[:-1]:  # Exclude current message
        if hasattr(message, 'content'):
            role = "User" if hasattr(message, 'type') and message.type == "human" else "Assistant"
            conversation_context += f"{role}: {message.content}\n"
    
    # Parse intent
    parsed_intent = parser.parse_intent(
        user_query=user_query,
        available_products=search_results,
        conversation_context=conversation_context,
        action_type=action_type
    )
    
    print(f"🔍 Intent Parser: {parsed_intent['reasoning']}")
    print(f"🎯 Selected SKUs: {parsed_intent['selected_skus']}")
    print(f"📊 Confidence: {parsed_intent['confidence']}")
    
    return {
        **state,
        "parsed_intent": parsed_intent
    } 