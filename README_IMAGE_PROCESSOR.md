# Integrated Image Processor

The image processor is now fully integrated into the image agent, making it intelligent enough to handle both local file uploads and existing product images automatically.

## How It Works

### 1. **Intelligent Request Analysis**

The image agent automatically analyzes user requests to determine the approach:

- **Local Files**: When users upload images and want to modify them
- **Product Images**: When users want to modify images of products from search results
- **File Requests**: When users mention image processing but haven't uploaded files yet

### 2. **Automatic Approach Selection**

The image agent uses the `analyze_image_request()` function to determine:

```python
# Example analysis results:
{
    "is_image_request": True,
    "has_uploaded_files": True,
    "files": [{"path": "/tmp/image.jpg", "filename": "image.jpg"}],
    "instruction": "Change background to coffee shop",
    "approach": "local_files"
}
```

### 3. **Three Processing Approaches**

#### A. **Local File Processing**

When users upload images:

1. Files are uploaded via `/v1/upload-files` endpoint
2. Image agent detects uploaded files in session state
3. Automatically uploads to S3 and processes with Replicate
4. Returns both original and modified image URLs

#### B. **Product Image Processing**

When users reference existing products:

1. Image agent uses intent parser to identify target products
2. Extracts image URLs from product metadata
3. Processes directly with Replicate
4. Integrates with listing database for Shopify preparation

#### C. **File Upload Requests**

When users want to process images but haven't uploaded:

1. Image agent detects image processing intent
2. Prompts user to upload files first
3. Provides clear instructions on supported formats

## API Endpoints

### Main Chat Endpoint

```http
POST /v1/chat/completions
Content-Type: application/json

{
    "messages": [
        {"role": "user", "content": "Change the background to a coffee shop"}
    ],
    "session_id": "optional-session-id"
}
```

### File Upload Endpoint

```http
POST /v1/upload-files
Content-Type: multipart/form-data

files: [image files]
session_id: "session-id"
```

## Usage Examples

### Example 1: Local File Processing

```bash
# 1. Upload image
curl -X POST http://localhost:8000/v1/upload-files \
  -F "files=@my_image.jpg" \
  -F "session_id=my_session"

# 2. Process image
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Change background to coffee shop"}],
    "session_id": "my_session"
  }'
```

### Example 2: Product Image Processing

```bash
# 1. Search for products
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Find me some products for coffee shops"}]
  }'

# 2. Modify product image
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Change the background of the first product to a coffee shop"}]
  }'
```

## Configuration

### Environment Variables

```bash
# Required for S3 uploads
S3_BUCKET_NAME=your-image-bucket
AWS_REGION=us-east-1

# Required for Replicate
REPLICATE_API_TOKEN=your-replicate-token

# Required for OpenAI
OPENAI_API_KEY=your-openai-key
```

### AWS Credentials

Ensure AWS credentials are configured via:

- AWS CLI: `aws configure`
- Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- IAM roles (if running on EC2)

## Key Features

### 1. **Automatic Intent Detection**

- No hardcoded keywords
- LLM-based intelligent routing
- Handles natural language variations

### 2. **Seamless Integration**

- Works with existing Shopify workflow
- Maintains session state
- Supports both local files and product images

### 3. **Error Handling**

- Graceful fallbacks for missing files
- Clear error messages
- Automatic cleanup of temporary files

### 4. **Flexible Processing**

- Supports multiple image formats
- Batch processing capabilities
- Customizable output formats

## Testing

Run the test suite to verify functionality:

```bash
python test_integrated_image_processor.py
```

This will test:

- Intent analysis
- API endpoints
- Product image workflow
- File upload workflow (requires S3 setup)

## Architecture

```
User Request → Planning Node → Image Agent → Intent Analysis → Processing
                                                      ↓
                                              ┌─────────────┬─────────────┐
                                              │ Local Files │ Product Imgs│
                                              └─────────────┴─────────────┘
                                                      ↓             ↓
                                              S3 Upload → Replicate → Response
```

The image agent is now a complete, intelligent image processing system that can handle any image modification request automatically!
