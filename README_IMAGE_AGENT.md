# Image Modification Agent

This document describes the image modification feature that allows users to modify product images with different backgrounds, styles, and transformations using AI.

## Overview

The Image Agent is a new component in the LangGraph workflow that can:

- Take product images from search results
- Apply text-based modifications (background changes, style transformations)
- Store modified images for use in Shopify listings
- Integrate seamlessly with the existing RAG and Shopify workflow

## How It Works

### 1. Image Agent Architecture

The image agent uses Replicate's Flux Kontext Pro model to modify images based on text instructions. It's designed as a modular component that can be easily integrated into the existing workflow.

### 2. Workflow Integration

```
User Query → Planning Node → Image Agent → GPT4 Chat → Response
                ↓
            Detects image modification requests
                ↓
            Routes to image_agent node
                ↓
            Modifies images using Replicate
                ↓
            Stores results in state
                ↓
            Returns to user via GPT4 Chat
```

### 3. Key Components

#### ImageAgent Class (`langgraph_workflow/nodes/image_agent.py`)

- `modify_image()`: Modifies a single image with text instruction
- `batch_modify_images()`: Modifies multiple images with the same instruction
- Uses Replicate's Flux Kontext Pro model for image transformations

#### Planning Node Updates (`langgraph_workflow/nodes/planning.py`)

- Detects image modification keywords in user queries
- Extracts target SKU from user input
- Routes requests to image_agent node
- Supports both specific SKU targeting and automatic selection

#### Graph Integration (`langgraph_workflow/graph_build.py`)

- Added `image_agent` node to the workflow
- Updated state schema to include image modification fields
- Added routing logic for image modification requests

#### Shopify Integration (`langgraph_workflow/nodes/shopify_agent.py`)

- Modified `create_media_from_metadata()` to include modified images
- Prioritizes modified images over original images in listings
- Maintains original images as additional views

## Usage Examples

### Basic Image Modification

```
User: "Find me a coffee table"
Assistant: [Shows coffee table products]

User: "Change the image to a coffee shop background"
Assistant: [Modifies the image and shows the result]
```

### Specific Product Modification

```
User: "Find me furniture for outdoor spaces"
Assistant: [Shows outdoor furniture products]

User: "Change ABC123 to have a garden background"
Assistant: [Modifies the specific product's image]
```

### Style Transformations

```
User: "Make this a 90s cartoon style"
User: "Turn this into a vintage photo"
User: "Convert this to a modern minimalist style"
```

## Supported Modifications

### Background Changes

- Coffee shop
- Office
- Bedroom
- Kitchen
- Living room
- Outdoor
- Garden
- Beach
- Mountain
- Cityscape

### Style Transformations

- 90s cartoon
- Vintage
- Modern
- Classic
- Artistic
- Professional
- Minimalist
- Retro
- Contemporary

### Color and Mood Changes

- Warm lighting
- Cool tones
- Dramatic lighting
- Soft lighting
- High contrast
- Low contrast

## Technical Implementation

### State Management

The workflow state includes new fields for image modification:

```python
class GraphState(TypedDict):
    # ... existing fields ...
    image_modification_request: dict  # User's modification request
    modified_images: list             # Results of image modifications
    image_agent_response: str         # Summary response from image agent
```

### Image Storage

- Modified images are stored in the workflow state
- Original images are preserved
- Modified images take priority in Shopify listings
- All images are accessible via URLs

### Error Handling

- Graceful handling of API failures
- Fallback to original images if modification fails
- Clear error messages for users
- Retry logic for transient failures

## Configuration

### Required Environment Variables

```bash
REPLICATE_API_TOKEN=your_replicate_token_here
```

### API Configuration

The image agent uses Replicate's Flux Kontext Pro model:

- Model: `black-forest-labs/flux-kontext-pro`
- Input: Image URL + text instruction
- Output: Modified image URL
- Format: JPG (default)

## Testing

Run the test script to verify the image agent functionality:

```bash
python test_image_agent.py
```

## Integration with Existing Features

### RAG Search

- Image agent works with products found through RAG search
- Automatically uses the main image from search results
- Supports multiple images per product

### Shopify Publishing

- Modified images are automatically used in Shopify listings
- Original images are kept as additional views
- Seamless integration with existing publishing workflow

### Multi-language Support

- Works with both English and Chinese queries
- Language detection for appropriate responses
- Localized error messages

## Future Enhancements

### Planned Features

1. **Batch Processing**: Modify multiple products at once
2. **Style Presets**: Predefined modification styles
3. **Image Quality Options**: Different resolution outputs
4. **Custom Backgrounds**: Upload custom background images
5. **A/B Testing**: Compare different modifications

### Technical Improvements

1. **Caching**: Cache modified images to reduce API calls
2. **Queue System**: Handle multiple modification requests
3. **Progress Tracking**: Real-time modification status
4. **Version Control**: Track modification history

## Troubleshooting

### Common Issues

1. **API Rate Limits**

   - Replicate has rate limits on API calls
   - Implement retry logic with exponential backoff
   - Consider caching for repeated modifications

2. **Image URL Issues**

   - Ensure image URLs are publicly accessible
   - Check for CORS restrictions
   - Validate image format compatibility

3. **Memory Management**
   - Large images may cause memory issues
   - Implement image resizing if needed
   - Monitor memory usage in production

### Debug Information

The image agent provides detailed logging:

- Modification requests and responses
- API call status and timing
- Error details and stack traces
- Performance metrics

## Security Considerations

1. **API Key Management**

   - Store Replicate API token securely
   - Use environment variables
   - Rotate keys regularly

2. **Image Validation**

   - Validate image URLs before processing
   - Check file size limits
   - Sanitize user inputs

3. **Data Privacy**
   - Images are processed by third-party APIs
   - Consider data retention policies
   - Implement user consent mechanisms

## Performance Optimization

1. **Parallel Processing**

   - Process multiple images concurrently
   - Use async/await for API calls
   - Implement connection pooling

2. **Caching Strategy**

   - Cache modified images locally
   - Use CDN for image delivery
   - Implement cache invalidation

3. **Resource Management**
   - Monitor API usage and costs
   - Implement usage quotas
   - Optimize image sizes

## Conclusion

The Image Modification Agent provides a powerful and flexible way to enhance product images for e-commerce applications. It integrates seamlessly with the existing workflow while providing users with creative control over their product presentations.

The modular design allows for easy extension and customization, while the robust error handling ensures reliable operation in production environments.
