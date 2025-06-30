import os
import time
import json
import tempfile
import requests
import boto3
import uuid
from typing import Dict, List, Any, Optional
import replicate
from langchain_core.messages import HumanMessage, AIMessage
from botocore.exceptions import NoCredentialsError
import config
from langchain_openai import ChatOpenAI

def select_products_for_image_modification(messages: List, search_results: List, user_query: str) -> List:
    """
    Use LLM to determine which products to modify based on conversation context and user query.
    """
    if not search_results:
        return []
    
    # Build conversation context
    conversation_parts = []
    for msg in messages[:-1]:  # Exclude the last message (current query)
        if hasattr(msg, 'content'):
            content = msg.content
            if isinstance(content, list):
                # Handle multimodal content
                text_parts = []
                for item in content:
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                content = " ".join(text_parts)
            conversation_parts.append(f"{'User' if hasattr(msg, 'type') and msg.type == 'human' else 'Assistant'}: {content}")
    
    conversation_context = "\n".join(conversation_parts[-10:])  # Last 10 messages
    
    # Build product list with descriptive names
    product_list = []
    for i, product in enumerate(search_results, 1):
        metadata = product.get('metadata', {})
        sku = metadata.get('sku', '')
        
        # Create descriptive name from available fields
        name_parts = []
        if metadata.get('category'):
            name_parts.append(metadata.get('category'))
        if metadata.get('material'):
            name_parts.append(metadata.get('material'))
        if metadata.get('color'):
            name_parts.append(metadata.get('color'))
        if metadata.get('characteristics_text'):
            name_parts.append(metadata.get('characteristics_text'))
        
        descriptive_name = " ".join(name_parts) if name_parts else f"Product {i}"
        
        product_info = f"{i}. SKU: {sku}, Name: {descriptive_name}"
        if metadata.get('scene'):
            product_info += f", Scene: {metadata.get('scene')}"
        
        product_list.append(product_info)
    
    product_list_text = "\n".join(product_list)
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
    
    prompt = f"""You are an expert at understanding user intent for image modification. Analyze the conversation and user query to determine which products should have their images modified.

CONVERSATION CONTEXT:
{conversation_context}

AVAILABLE PRODUCTS:
{product_list_text}

USER'S CURRENT QUERY:
{user_query}

TASK: Determine which products the user wants to modify images for based on their query and conversation context.

INSTRUCTIONS:
1. Look for specific product references in the user's query (e.g., "this sofa", "the black table", "最后这个", "这款", "put this on balcony")
2. Consider the conversation context to understand what products were discussed
3. If the user says "put this in X" or "place this in Y", they're referring to the most recently discussed product
4. If the user mentions specific characteristics (color, material, etc.), match those to products
5. If the user doesn't specify which product, use the most recently discussed product
6. Pay attention to order - "最后这个" (last one) refers to the most recent product in the list
7. For image modification requests, it's usually safe to assume they want to modify the most relevant product

EXAMPLES:
- "put this sofa on the balcony" → Select the most recently discussed sofa
- "最后这个sku，黑桌子可以" → Select the last product if it's a black table
- "这款" → Select the most recently discussed product
- "change the background to coffee shop" → Select the most recently discussed product
- "modify the chair" → Select products that are chairs

Return a JSON response with:
{{
    "selected_skus": ["SKU1", "SKU2", ...],
    "reasoning": "Explanation of why these products were selected",
    "confidence": 0.95
}}

If you can't determine specific products, return an empty array for selected_skus and explain why.

Response:"""

    try:
        response = llm.invoke(prompt)
        result = json.loads(response.content.strip())
        
        selected_skus = result.get("selected_skus", [])
        reasoning = result.get("reasoning", "")
        confidence = result.get("confidence", 0.0)
        
        print(f"🤖 LLM Image Product Selection:")
        print(f"   Reasoning: {reasoning}")
        print(f"   Selected SKUs: {selected_skus}")
        print(f"   Confidence: {confidence}")
        
        if selected_skus:
            # Filter products based on selected SKUs
            filtered_products = []
            for product in search_results:
                sku = product.get('metadata', {}).get('sku', '')
                if sku in selected_skus:
                    filtered_products.append(product)
            
            if filtered_products:
                return filtered_products
            else:
                print(f"⚠️ No matching products found for selected SKUs: {selected_skus}")
                return search_results  # Fallback to all products
        else:
            print("🔍 No specific products selected, using most recent product")
            # Use the most recent product if no specific selection
            return search_results[:1] if search_results else []
            
    except Exception as e:
        print(f"❌ Error in LLM product selection: {e}")
        return search_results[:1] if search_results else []  # Fallback to first product

def generate_replicate_prompt(user_instruction: str, conversation_context: str = "", previous_modifications: List[Dict] = None) -> str:
    """
    Use LLM to generate a concise English prompt for Replicate based on user request and context.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    
    # Build context information
    context_info = ""
    if conversation_context:
        context_info += f"\nConversation Context:\n{conversation_context}"
    
    if previous_modifications:
        context_info += "\nPrevious Modifications:\n"
        for i, mod in enumerate(previous_modifications[-2:], 1):  # Last 2 modifications
            if mod.get('status') == 'success':
                context_info += f"- Previous {i}: {mod.get('instruction', 'Unknown')}\n"
    
    # Analyze if this is a correction request
    correction_indicators = [
        "why", "wrong", "incorrect", "mistake", "error", "don't like", "don't want",
        "shouldn't", "should be", "fix", "correct", "change", "adjust", "modify",
        "problem", "issue", "confused", "don't understand", "not what I asked"
    ]
    
    is_correction_request = any(indicator in user_instruction.lower() for indicator in correction_indicators)
    
    if is_correction_request:
        prompt = f"""You are an expert at writing concise prompts for AI image modification models.

TASK: Generate a brief correction prompt (1-2 sentences max) that addresses the user's concern.

USER'S CORRECTION REQUEST: {user_instruction}

{context_info}

INSTRUCTIONS:
- Write a clear, concise English prompt (1-2 sentences maximum)
- Be specific about what needs to be fixed
- Use simple, direct language
- Focus on the main issue only

EXAMPLES:
User: "为什么椅子在桌子上？"
Prompt: "Place the chair on the floor in a proper position, not on the table."

User: "I don't like the background, it's too dark"
Prompt: "Change the background to a brighter, well-lit environment while keeping the main subject unchanged."

Write the correction prompt:"""
    else:
        prompt = f"""You are an expert at writing concise prompts for AI image modification models.

TASK: Convert the user's request into a brief, clear English prompt (1-2 sentences max).

USER REQUEST: {user_instruction}

{context_info}

INSTRUCTIONS:
- Write a clear, concise English prompt (1-2 sentences maximum)
- Be specific about what should change and what should stay the same
- Use simple, direct language that image models understand
- Focus on the main transformation only

EXAMPLE:
User: "把这款椅子的背景改成咖啡店，带人，椅子保持不变"
Prompt: "Replace the background with a coffee shop interior featuring people, while keeping the chair exactly as it is."

Write the English prompt:"""

    response = llm.invoke(prompt)
    return response.content.strip()

def translate_instruction_to_english(user_instruction: str) -> str:
    """
    Smart interpretation and prompt generation for Replicate API.
    Interprets user intent and creates detailed, professional prompts.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
    
    prompt = f"""You are an expert at interpreting user requests and creating detailed, professional prompts for image generation models.

USER REQUEST: "{user_instruction}"

TASK: Analyze the user's request and create a comprehensive, detailed English prompt that will produce the best possible image modification results.

ANALYSIS GUIDELINES:
1. **Understand the core intent** - What does the user actually want to achieve?
2. **Identify key elements** - What should change? What should stay the same?
3. **Add missing details** - Fill in context that would help the model understand better
4. **Use professional terminology** - Use terms that image generation models understand well
5. **Be specific about style and quality** - Mention lighting, composition, realism, etc.

PROMPT STRUCTURE:
- Start with the main action/transformation
- Specify what elements should remain unchanged
- Add environmental/contextual details
- Include style and quality specifications
- Mention any specific requirements (lighting, angle, etc.)

EXAMPLES:

User: "把这款椅子的背景改成咖啡店，带人，椅子保持不变"
Smart Prompt: "Transform the background into a warm, inviting coffee shop interior while keeping the chair completely unchanged. The coffee shop should feature baristas working behind a counter, customers sitting at tables, warm ambient lighting, coffee machines, and a cozy atmosphere. The chair should remain exactly as it is - same color, texture, position, and lighting. Create a realistic, high-quality image with natural lighting and professional composition."

User: "这款黄色的亚麻椅子不错，帮我做一张咖啡店背景的图，后面有人，椅子不变"
Smart Prompt: "Create a sophisticated coffee shop scene as the background while preserving the yellow linen chair exactly as it appears. The coffee shop should have a modern, upscale interior with people in the background - baristas preparing coffee, customers working on laptops, and a relaxed atmosphere. The chair should maintain its original yellow linen texture, shape, and positioning. Use natural lighting, high resolution, and professional photography style."

User: "change the background to a modern office"
Smart Prompt: "Replace the background with a contemporary office environment featuring clean lines, modern furniture, large windows with natural light, and a professional atmosphere. The main subject should remain unchanged in position, lighting, and appearance. Include office elements like desks, computers, plants, and subtle ambient lighting. Maintain high quality and realistic composition."

User: "make this look like a 90s cartoon"
Smart Prompt: "Transform the image into a vibrant 90s cartoon style with bold colors, exaggerated features, and retro aesthetics. Apply cel-shading, bright saturated colors, and classic 90s animation characteristics while maintaining the core subject and composition. Use a nostalgic color palette with neon accents and smooth, clean lines typical of 90s cartoon art."

Create a detailed, professional prompt that will produce excellent results:"""

    try:
        response = llm.invoke(prompt)
        smart_prompt = response.content.strip()
        print(f"🧠 Smart Prompt Generation:")
        print(f"   Original: '{user_instruction}'")
        print(f"   Enhanced: '{smart_prompt}'")
        return smart_prompt
    except Exception as e:
        print(f"⚠️ Smart prompt generation failed, using original: {e}")
        return user_instruction

class ImageProcessor:
    def __init__(self, bucket_name: str = None, region: str = None):
        self.bucket_name = bucket_name or config.S3_BUCKET_NAME
        self.region = region or config.AWS_REGION
        
        # Create S3 client with credentials from config
        if self.bucket_name and self.bucket_name != "your-image-bucket":
            self.s3_client = boto3.client(
                "s3", 
                region_name=self.region,
                aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY
            )
        else:
            self.s3_client = None
            
        self.replicate_client = replicate.Client(api_token=config.REPLICATE_API_TOKEN)
    
    def upload_to_s3(self, image_path: str, object_name: Optional[str] = None) -> str:
        """
        Uploads an image to AWS S3 and returns the public URL.
        """
        if not self.bucket_name or self.bucket_name == "your-image-bucket":
            raise Exception("S3_BUCKET_NAME not configured")
            
        if object_name is None:
            object_name = f"uploads/{uuid.uuid4()}_{os.path.basename(image_path)}"
        
        try:
            # Upload the file to S3
            self.s3_client.upload_file(
                image_path, 
                self.bucket_name, 
                object_name, 
                ExtraArgs={"ACL": "public-read"}
            )
            
            # Generate the public URL
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{object_name}"
            print(f"✅ File uploaded successfully: {url}")
            return url
            
        except FileNotFoundError:
            raise Exception("The file was not found.")
        except NoCredentialsError:
            raise Exception("AWS credentials not available.")
        except Exception as e:
            raise Exception(f"Upload failed: {e}")
    
    def process_local_image(self, image_path: str, instruction: str, output_format: str = "jpg") -> Dict[str, Any]:
        """
        Process a local image: upload to S3, modify with Replicate, return results.
        """
        print(f"🎨 Processing local image: {image_path}")
        print(f"🎨 Instruction: {instruction}")
        
        # Step 1: Upload to S3
        print("📤 Uploading image to S3...")
        original_url = self.upload_to_s3(image_path)
        
        # Step 2: Process with Replicate
        return self._process_with_replicate(original_url, instruction, output_format, image_path)
    
    def process_url_image(self, image_url: str, instruction: str, output_format: str = "jpg") -> Dict[str, Any]:
        """
        Process an existing image URL with Replicate.
        """
        print(f"🎨 Processing URL image: {image_url}")
        print(f"🎨 Instruction: {instruction}")
        
        return self._process_with_replicate(image_url, instruction, output_format)
    
    def _process_with_replicate(self, image_url: str, instruction: str, output_format: str = "jpg", original_file: str = None) -> Dict[str, Any]:
        """
        Process image with Replicate (internal method).
        """
        print("🔄 Processing with Replicate...")
        try:
            # Translate instruction to English for Replicate API
            english_instruction = translate_instruction_to_english(instruction)
            
            # Use Flux Kontext Pro model with correct parameters
            input_data = {
                "prompt": english_instruction,
                "input_image": image_url,
                "output_format": output_format
            }
            
            print(f"🎨 Replicate input data: {input_data}")
            
            # Run the model with correct parameters
            output = self.replicate_client.run(
                "black-forest-labs/flux-kontext-pro",
                input=input_data
            )
            
            # Convert FileOutput to string URL
            if hasattr(output, 'url'):
                modified_url = str(output.url)
            elif isinstance(output, str):
                modified_url = output
            elif isinstance(output, list) and len(output) > 0:
                modified_url = str(output[0])
            else:
                modified_url = str(output)
            
            print(f"✅ Image processing complete!")
            print(f"✅ Modified image URL: {modified_url}")
            
            result = {
                "original_url": image_url,
                "modified_url": modified_url,
                "instruction": instruction,
                "english_instruction": english_instruction,
                "status": "success",
                "timestamp": time.time()
            }
            
            if original_file:
                result["original_file"] = original_file
            
            return result
            
        except Exception as e:
            print(f"❌ Replicate processing failed: {e}")
            result = {
                "original_url": image_url,
                "modified_url": None,
                "instruction": instruction,
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
            
            if original_file:
                result["original_file"] = original_file
            
            return result

class ImageAgent:
    def __init__(self):
        self.replicate_client = replicate.Client(api_token=config.REPLICATE_API_TOKEN)
        self.image_processor = ImageProcessor()
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
        return self.image_processor.process_url_image(image_url, instruction, output_format)
    
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

def analyze_image_request(user_query: str, uploaded_files: List[Dict] = None) -> Dict[str, Any]:
    """
    Analyze the user query to determine if it's an image modification request and what approach to use.
    """
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        prompt = f"""You are an expert at analyzing user requests for image modification. ..."""
        response = llm.invoke(prompt)
        result = json.loads(response.content.strip())
        is_image_request = result.get("is_image_request", False)
        approach = result.get("approach", "none")
        reasoning = result.get("reasoning", "")
        print(f"🤖 LLM Image Analysis:")
        print(f"   Query: {user_query}")
        print(f"   Is image request: {is_image_request}")
        print(f"   Approach: {approach}")
        print(f"   Reasoning: {reasoning}")
        if approach == "product_images":
            return {
                "is_image_request": True,
                "has_uploaded_files": False,
                "instruction": user_query,
                "approach": "product_images"
            }
        elif approach == "need_files":
            return {
                "is_image_request": True,
                "has_uploaded_files": False,
                "instruction": user_query,
                "approach": "need_files"
            }
        else:
            return {
                "is_image_request": False,
                "approach": "none"
            }
    except Exception as e:
        print(f"❌ Error in LLM image analysis: {e}")
        # Fallback to simple keyword check
        if any(keyword in user_query.lower() for keyword in ['modify', 'change', 'edit', 'background', 'image', 'photo']):
            return {
                "is_image_request": True,
                "has_uploaded_files": False,
                "instruction": user_query,
                "approach": "need_files"
            }
    return {
        "is_image_request": False,
        "approach": "none"
    }

def image_agent_node(state):
    """
    LangGraph node for image modification - WORKFLOW VERSION
    This handles image modification when user is in the product search workflow.
    
    Expects state to contain:
    - image_modification_request: Dict with 'instruction'
    - search_results: List of products (for context)
    - uploaded_files: List of uploaded file info (optional)
    
    Returns state with:
    - modified_images: List of modified image results
    - image_agent_response: Summary of modifications
    - awaiting_confirmation: Boolean to indicate waiting for user confirmation
    """
    print("🔄 LangGraph: Executing 'workflow_image_agent' node...")
    
    # Debug: Log what we received in state
    print(f"🔍 Image Agent Debug - image_modification_request: {state.get('image_modification_request')}")
    print(f"🔍 Image Agent Debug - search_results length: {len(state.get('search_results', []))}")
    print(f"🔍 Image Agent Debug - uploaded_files: {state.get('uploaded_files', [])}")
    
    # Initialize the image agent
    agent = ImageAgent()
    
    # Get the modification request and search results from state
    modification_request = state.get("image_modification_request", {})
    search_results = state.get("search_results", [])
    uploaded_files = state.get("uploaded_files", [])
    user_query = state["messages"][-1].content
    
    # PRIORITY 1: If user uploaded files, process them first
    if uploaded_files:
        print("🎨 Image Agent: User uploaded files - processing uploaded files")
        analysis = {
            "is_image_request": True,
            "has_uploaded_files": True,
            "files": uploaded_files,
            "instruction": user_query,
            "approach": "local_files"
        }
        return _process_local_files(agent, state, analysis, user_query)
    
    # PRIORITY 2: User wants to modify product images from search results
    if search_results:
        print("🎨 Image Agent: Processing existing product images from search results")
        return _process_product_images(agent, state, modification_request, search_results, user_query)
    
    # PRIORITY 3: No search results, ask user to search first
    print("🎨 Image Agent: No search results, asking user to search first")
    is_chinese = any('\u4e00' <= char <= '\u9fff' for char in user_query)
    
    if is_chinese:
        response_text = f"""🤔 **需要先找到产品**

我理解你想要修改图片：*"{user_query}"*

但是我没有找到任何产品可以修改。这可能是因为：
1. 你还没有搜索过产品
2. 或者会话已经重置了

**请先搜索产品：**
- 说 "帮我看看有没有沙发" 或 "找一些家具"
- 然后再说 "把这个沙发放到阳台"

这样我就能知道你要修改哪个产品了！😊"""
    else:
        response_text = f"""🤔 **Need to Find Products First**

I understand you want to modify images: *"{user_query}"*

But I couldn't find any products to modify. This might be because:
1. You haven't searched for products yet
2. Or the session was reset

**Please search for products first:**
- Say "help me find some sofas" or "look for furniture"
- Then say "put this sofa on the balcony"

This way I'll know which product you want to modify! 😊"""
    
    return {
        **state,
        "modified_images": [],
        "image_agent_response": response_text,
        "messages": state.get("messages", []) + [AIMessage(content=response_text)],
        "awaiting_confirmation": False
    }

def _process_local_files(agent: ImageAgent, state: Dict, analysis: Dict, user_query: str) -> Dict:
    """Process uploaded local files."""
    uploaded_files = analysis["files"]
    user_instruction = analysis["instruction"]
    
    print(f"🎨 Processing {len(uploaded_files)} uploaded images")
    
    # IMPORTANT: Clear uploaded files BEFORE processing to prevent accumulation
    state["uploaded_files"] = []
    
    # Build conversation context for better prompt generation
    conversation_context = ""
    messages = state.get("messages", [])
    if len(messages) > 1:
        # Get the last few messages for context (excluding the current one)
        recent_messages = messages[-4:-1]  # Last 3 messages before current
        conversation_context = "\n".join([
            f"Message {i}: {msg.content[:200]}{'...' if len(msg.content) > 200 else ''}"
            for i, msg in enumerate(recent_messages, 1)
            if hasattr(msg, 'content')
        ])
    
    # Get previous modifications for context
    previous_modifications = state.get("modified_images", [])
    
    # Generate proper English prompt for Replicate using LLM (always in English for API)
    print(f"🎨 Generating Replicate prompt for: {user_instruction}")
    replicate_prompt = generate_replicate_prompt(
        user_instruction=user_instruction,
        conversation_context=conversation_context,
        previous_modifications=previous_modifications
    )
    print(f"🎨 Generated Replicate prompt: {replicate_prompt}")
    
    # Process each uploaded image with the generated prompt
    results = []
    for i, file_info in enumerate(uploaded_files, 1):
        file_path = file_info.get("path")
        if file_path and os.path.exists(file_path):
            try:
                print(f"🎨 Processing image {i}/{len(uploaded_files)}: {os.path.basename(file_path)}")
                result = agent.image_processor.process_local_image(file_path, replicate_prompt)
                # Store both the original user instruction and the generated prompt
                result["user_instruction"] = user_instruction
                result["replicate_prompt"] = replicate_prompt
                results.append(result)
                print(f"✅ Completed image {i}/{len(uploaded_files)}")
            except Exception as e:
                print(f"❌ Failed to process {file_path}: {e}")
                results.append({
                    "original_file": file_path,
                    "status": "error",
                    "error": str(e),
                    "user_instruction": user_instruction,
                    "replicate_prompt": replicate_prompt
                })
    
    # Create response based on user's language
    successful_results = [r for r in results if r.get("status") == "success"]
    failed_results = [r for r in results if r.get("status") == "error"]
    
    # Detect if user is speaking Chinese
    is_chinese = any('\u4e00' <= char <= '\u9fff' for char in user_query)
    
    if successful_results:
        if is_chinese:
            response_text = f"""🎨 **图片处理完成！**\n\n我已成功按照你的要求 *\"{user_instruction}\"* 处理了 **{len(successful_results)} 张图片**。\n\n**结果：**\n"""
            for i, result in enumerate(successful_results, 1):
                response_text += f"""\n**图片 {i}:**\n\n**原图：**\n![原图 {i}]({result['original_url']})\n\n**修改后图片：**\n![修改后图片 {i}]({result['modified_url']})\n\n---\n"""
            if failed_results:
                response_text += f"\n**失败：** {len(failed_results)} 张图片处理失败。"
            response_text += f"""\n\n太棒了！这些图片修改得怎么样？😊\n\n**请确认：** 你想要将这些修改后的图片加入到上架准备数据库中吗？\n- 回复 **\"是\"** 或 **\"yes\"** 来添加\n- 回复 **\"否\"** 或 **\"no\"** 来放弃修改"""
        else:
            response_text = f"""🎨 **Image Processing Complete!**\n\nI've successfully processed **{len(successful_results)} image(s)** with your instruction: *\"{user_instruction}\"*\n\n**Results:**\n"""
            for i, result in enumerate(successful_results, 1):
                response_text += f"""\n**Image {i}:**\n\n**Original Image:**\n![Original Image {i}]({result['original_url']})\n\n**Modified Image:**\n![Modified Image {i}]({result['modified_url']})\n\n---\n"""
            if failed_results:
                response_text += f"\n**Failed:** {len(failed_results)} images could not be processed."
            response_text += f"""\n\nAwesome! How do these image modifications look? 😊\n\n**Please confirm:** Would you like to add these modified images to the listing preparation database?\n- Reply **\"yes\"** to add them\n- Reply **\"no\"** to discard the modifications"""
    else:
        if is_chinese:
            response_text = f"""❌ **图片处理失败**\n\n我无法处理任何图片，按照你的要求：*\"{user_instruction}\"*\n\n**遇到的问题：**\n"""
            for result in failed_results:
                response_text += f"- {result.get('original_file', '未知文件')}: {result.get('error', '未知错误')}\n"
        else:
            response_text = f"""❌ **Image Processing Failed**\n\nI was unable to process any images with your instruction: *\"{user_instruction}\"*\n\n**Issues encountered:**\n"""
            for result in failed_results:
                response_text += f"- {result.get('original_file', 'Unknown file')}: {result.get('error', 'Unknown error')}\n"
    
    # Clean up temporary files
    for file_info in uploaded_files:
        file_path = file_info.get("path")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️ Cleaned up temporary file: {file_path}")
            except Exception as e:
                print(f"⚠️ Failed to clean up {file_path}: {e}")
    
    return {
        **state,
        "modified_images": results,
        "image_agent_response": response_text,
        "messages": state.get("messages", []) + [AIMessage(content=response_text)],
        "awaiting_confirmation": False
    }

def _process_product_images(agent: ImageAgent, state: Dict, modification_request: Dict, search_results: List, user_query: str) -> Dict:
    """Process existing product images with SKU identification."""
    print("🎨 Image Agent: Processing product images with SKU identification")
    
    # Use LLM to identify which specific product/SKU the user is referring to
    identified_sku = _identify_sku_with_llm(user_query, search_results, state.get("messages", []))

    if not identified_sku:
        # Could not identify a SKU at all
        is_chinese = any('\u4e00' <= char <= '\u9fff' for char in user_query)
        if is_chinese:
            response_text = f"""❌ **无法识别产品**\n\n我无法确定你要修改哪个产品。请明确指定产品或SKU。"""
        else:
            response_text = f"""❌ **Could Not Identify Product**\n\nI couldn't determine which product you want to modify. Please specify a product or SKU."""
        return {
            **state,
            "modified_images": [],
            "image_agent_response": response_text,
            "messages": state.get("messages", []) + [AIMessage(content=response_text)],
            "awaiting_confirmation": False
        }

    # Only look up the product in the listing database
    target_product = None
    try:
        from .listing_database import ListingDatabase
        db = ListingDatabase()
        listing_product = db.get_product(identified_sku)
        if listing_product and listing_product.get('original_metadata'):
            print(f"🔍 Found SKU {identified_sku} in listing database.")
            target_product = {'metadata': listing_product['original_metadata']}
    except Exception as e:
        print(f"⚠️ Error checking listing database for SKU {identified_sku}: {e}")
    
    if not target_product:
        # SKU not found in listing database
        is_chinese = any('\u4e00' <= char <= '\u9fff' for char in user_query)
        if is_chinese:
            response_text = f"""❌ **产品未找到**\n\n抱歉，我在上架数据库中找不到SKU为 **{identified_sku}** 的产品。\n\n请重新搜索产品，或者指定一个可用的产品。"""
        else:
            response_text = f"""❌ **Product Not Found**\n\nSorry, I couldn't find a product with SKU **{identified_sku}** in the listing database.\n\nPlease search for products again, or specify an available product."""
        return {
            **state,
            "modified_images": [],
            "image_agent_response": response_text,
            "messages": state.get("messages", []) + [AIMessage(content=response_text)],
            "awaiting_confirmation": False
        }
    
    # Process the identified product
    print(f"🎨 Image Agent: Processing product SKU {identified_sku}")
    
    # Get product image URL
    metadata = target_product.get('metadata', {})
    image_url = (
        metadata.get('main_image_url') or
        (metadata.get('image_urls')[0] if metadata.get('image_urls') else None) or
        metadata.get('image_url')
    )
    if not image_url:
        is_chinese = any('\u4e00' <= char <= '\u9fff' for char in user_query)
        
        if is_chinese:
            response_text = f"""❌ **产品图片不可用**

抱歉，产品 **{identified_sku}** 没有可用的图片。

请选择其他有图片的产品进行修改。"""
        else:
            response_text = f"""❌ **Product Image Not Available**

Sorry, product **{identified_sku}** doesn't have an available image.

Please select another product with an image for modification."""
        
        return {
            **state,
            "modified_images": [],
            "image_agent_response": response_text,
            "messages": state.get("messages", []) + [AIMessage(content=response_text)],
            "awaiting_confirmation": False
        }
    
    # Build conversation context for the image modification
    conversation_context = _build_conversation_context(state.get("messages", []), [target_product])
    
    # Get previous modifications for this product
    previous_modifications = []
    modified_images = state.get("modified_images", [])
    for mod in modified_images:
        if mod.get('sku') == identified_sku:
            previous_modifications.append(mod)
    
    # Process the image
    try:
        result = agent.modify_image(
            image_url=image_url,
            instruction=user_query,
            output_format="jpg"
        )
        
        if result.get('status') == 'success':
            # Successfully modified the image
            modified_image_url = result.get('modified_url')
            
            # Add to modified images list
            new_modified_image = {
                'sku': identified_sku,
                'original_url': image_url,
                'modified_url': modified_image_url,
                'instruction': user_query,
                'status': 'success'
            }
            
            updated_modified_images = modified_images + [new_modified_image]
            
            # Generate response
            is_chinese = any('\u4e00' <= char <= '\u9fff' for char in user_query)
            
            if is_chinese:
                response_text = f"""🎨 **图片修改完成**

按照你的要求 *"{user_query}"* 成功修改了产品 **{identified_sku}** 的图片：

**原图：**
![原图]({image_url})

**修改后：**
![修改后]({modified_image_url})

太棒了！这个修改效果怎么样？😊

**请确认：** 你想要将这个修改后的图片添加到上架准备数据库中吗？
- 回复 **"是"** 或 **"yes"** 来添加
- 回复 **"否"** 或 **"no"** 来放弃修改"""
            else:
                response_text = f"""🎨 **Image Modification Complete**

Successfully modified the image for product **{identified_sku}** with your instruction: *"{user_query}"*

**Original Image:**
![Original]({image_url})

**Modified Image:**
![Modified]({modified_image_url})

Awesome! How does this modification look? 😊

**Please confirm:** Would you like to add this modified image to the listing preparation database?
- Reply **"yes"** to add it
- Reply **"no"** to discard the modification"""
            
            return {
                **state,
                "modified_images": updated_modified_images,
                "image_agent_response": response_text,
                "messages": state.get("messages", []) + [AIMessage(content=response_text)],
                "awaiting_confirmation": True
            }
        else:
            # Failed to modify the image
            error_msg = result.get('error', 'Unknown error')
            print(f"❌ Image Agent: Failed to modify image: {error_msg}")
            
            is_chinese = any('\u4e00' <= char <= '\u9fff' for char in user_query)
            
            if is_chinese:
                response_text = f"""❌ **图片修改失败**

很抱歉，按照你的要求 *"{user_query}"* 修改产品 **{identified_sku}** 的图片时遇到了问题。

**错误信息：** {error_msg}

请尝试：
1. 重新描述你的修改要求
2. 选择其他产品
3. 稍后再试"""
            else:
                response_text = f"""❌ **Image Modification Failed**

Sorry, I encountered issues modifying the image for product **{identified_sku}** with your instruction: *"{user_query}"*

**Error:** {error_msg}

Please try:
1. Rephrasing your modification request
2. Selecting a different product
3. Trying again later"""
            
            return {
                **state,
                "modified_images": modified_images,
                "image_agent_response": response_text,
                "messages": state.get("messages", []) + [AIMessage(content=response_text)],
                "awaiting_confirmation": False
            }
    except Exception as e:
        print(f"❌ Image Agent: Exception during image modification: {str(e)}")
        is_chinese = any('\u4e00' <= char <= '\u9fff' for char in user_query)
        if is_chinese:
            response_text = f"""❌ **图片修改出错**\n\n很抱歉，处理产品 **{identified_sku}** 的图片时出现了意外错误。\n\n**错误：** {str(e)}\n\n请稍后再试，或者联系技术支持。"""
        else:
            response_text = f"""❌ **Image Modification Error**\n\nSorry, an unexpected error occurred while processing the image for product **{identified_sku}**.\n\n**Error:** {str(e)}\n\nPlease try again later, or contact support."""
        return {
            **state,
            "modified_images": modified_images,
            "image_agent_response": response_text,
            "messages": state.get("messages", []) + [AIMessage(content=response_text)],
            "awaiting_confirmation": False
        }


def _identify_sku_with_llm(user_query: str, search_results: List[Dict], messages: List) -> Optional[str]:
    """
    Use LLM to identify which SKU the user is referring to.
    
    Args:
        user_query: The current user query
        search_results: Current search results
        messages: Full conversation history
    
    Returns:
        The identified SKU string, or None if cannot identify
    """
    try:
        # Build conversation context
        conversation_context = _build_conversation_context(messages, search_results)
        
        # Create the prompt for SKU identification
        prompt = f"""You are an AI assistant that helps identify which specific product (SKU) a user is referring to.

**Current User Query:** {user_query}

**Conversation Context:**
{conversation_context}

**Available Products:**
{_format_products_for_llm(search_results)}

**Your Task:**
1. Analyze the user's query and conversation context
2. Identify which specific product/SKU they are referring to
3. Return ONLY the SKU number (e.g., "W1880115228") or "none" if you cannot identify

**Common Reference Patterns:**
- "这个黄色亚麻凳子" → refers to a yellow linen stool/chair
- "这个沙发" → refers to the most recently mentioned sofa
- "黑色的桌子" → refers to a table with black color
- "第二个产品" → refers to the second product in the list
- "最后这个" → refers to the last product mentioned
- "W1880115228" → direct SKU reference

**Important Rules:**
- If user mentions specific characteristics (color, material, type), match to products with those features
- "黄色" (yellow) should match products with yellow color
- "亚麻" (linen) should match products with linen material
- "凳子" (stool/chair) should match chair/stool category products
- If user says "这个" (this) with characteristics, look for products matching those characteristics
- If no clear reference can be made, return "none"

**Response Format:**
Return ONLY the SKU string or "none". No explanations.

Example responses:
- "W1880115228"
- "none"
"""

        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=50
        )
        
        # Get LLM response
        response = llm.invoke(prompt)
        identified_sku = response.content.strip()
        
        print(f"🔍 Image Agent SKU Identification LLM Response: {identified_sku}")
        
        # Validate the response
        if identified_sku.lower() == "none" or not identified_sku:
            return None
        
        # Check if it looks like a valid SKU (basic validation)
        if len(identified_sku) >= 8 and any(char.isdigit() for char in identified_sku):
            return identified_sku
        
        return None
        
    except Exception as e:
        print(f"❌ Image Agent SKU Identification LLM Error: {str(e)}")
        return None


def _build_conversation_context(messages: List, search_results: List[Dict]) -> str:
    """Build conversation context for LLM analysis."""
    context_parts = []
    
    # Add recent conversation (last 10 messages)
    recent_messages = messages[-10:] if len(messages) > 10 else messages
    for msg in recent_messages:
        role = "User" if hasattr(msg, 'type') and msg.type == 'human' else "Assistant"
        content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
        context_parts.append(f"{role}: {content}")
    
    # Add product search context
    if search_results:
        context_parts.append(f"\n**Recently Found Products:** {len(search_results)} products")
        for i, product in enumerate(search_results[-3:], 1):  # Last 3 products
            sku = product.get('metadata', {}).get('sku', 'N/A')
            name = product.get('metadata', {}).get('name', 'N/A')
            context_parts.append(f"  {i}. SKU: {sku} - {name}")
    
    return "\n".join(context_parts)


def _format_products_for_llm(products: List[Dict]) -> str:
    """Format products for LLM analysis."""
    if not products:
        return "No products available"
    
    formatted = []
    for i, product in enumerate(products, 1):
        metadata = product.get('metadata', {})
        sku = metadata.get('sku', 'N/A')
        category = metadata.get('category', 'N/A')
        material = metadata.get('material', 'N/A')
        color = metadata.get('color', 'N/A')
        characteristics = metadata.get('characteristics_text', 'N/A')
        
        # Create a descriptive name from available fields
        name_parts = []
        if category and category != 'N/A':
            name_parts.append(category)
        if material and material != 'N/A':
            name_parts.append(material)
        if color and color != 'N/A':
            name_parts.append(color)
        
        descriptive_name = " ".join(name_parts) if name_parts else f"Product {i}"
        
        formatted.append(f"{i}. SKU: {sku}")
        formatted.append(f"   Description: {descriptive_name}")
        formatted.append(f"   Category: {category}")
        formatted.append(f"   Material: {material}")
        formatted.append(f"   Color: {color}")
        if characteristics and characteristics != 'N/A':
            formatted.append(f"   Characteristics: {characteristics[:100]}...")
        formatted.append("")
    
    return "\n".join(formatted) 