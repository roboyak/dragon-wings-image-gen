#!/bin/bash

# Dragon Wings AI Image Generator - API Test Script

set -e

API_URL="http://localhost:8000"

echo "🐉 Dragon Wings AI Image Generator - API Test"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${BLUE}Test 1: Health Check${NC}"
echo "GET $API_URL/api/health"
echo ""
curl -s $API_URL/api/health | jq .
echo ""
echo -e "${GREEN}✅ Health check passed${NC}"
echo ""

# Test 2: List Models
echo -e "${BLUE}Test 2: List Available Models${NC}"
echo "GET $API_URL/api/models"
echo ""
curl -s $API_URL/api/models | jq .
echo ""
echo -e "${GREEN}✅ Models list retrieved${NC}"
echo ""

# Test 3: Generate Image
echo -e "${BLUE}Test 3: Generate Image${NC}"
echo "POST $API_URL/api/generate"
echo ""
echo "Prompt: 'A serene landscape with mountains and a lake at sunset'"
echo "This will take 5-30 seconds depending on your hardware..."
echo ""

RESPONSE=$(curl -s -X POST $API_URL/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A serene landscape with mountains and a lake at sunset, highly detailed, 4k",
    "negative_prompt": "blurry, low quality, distorted",
    "num_inference_steps": 25,
    "guidance_scale": 7.5,
    "width": 512,
    "height": 512,
    "seed": 42
  }')

echo "$RESPONSE" | jq .
echo ""

# Extract job_id
JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')

if [ "$JOB_ID" == "null" ] || [ -z "$JOB_ID" ]; then
    echo -e "${YELLOW}⚠️  Failed to get job_id. Is the server running?${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Job queued: $JOB_ID${NC}"
echo ""

# Test 4: Poll for Status
echo -e "${BLUE}Test 4: Check Generation Status${NC}"
echo "GET $API_URL/api/status/$JOB_ID"
echo ""
echo "Polling for completion..."
echo ""

MAX_ATTEMPTS=60
ATTEMPT=0
STATUS="pending"

while [ "$STATUS" != "completed" ] && [ "$STATUS" != "failed" ] && [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    sleep 2
    ATTEMPT=$((ATTEMPT + 1))

    STATUS_RESPONSE=$(curl -s $API_URL/api/status/$JOB_ID)
    STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')

    echo -e "${YELLOW}Attempt $ATTEMPT/$MAX_ATTEMPTS - Status: $STATUS${NC}"

    if [ "$STATUS" == "completed" ]; then
        echo ""
        echo "$STATUS_RESPONSE" | jq .
        echo ""
        echo -e "${GREEN}✅ Image generated successfully!${NC}"

        # Show image location
        IMAGE_URL=$(echo "$STATUS_RESPONSE" | jq -r '.image_url')
        IMAGE_FILE="generated_images/$(basename $IMAGE_URL)"

        if [ -f "$IMAGE_FILE" ]; then
            echo ""
            echo "📁 Image saved to: $IMAGE_FILE"
            echo "💡 View with: open $IMAGE_FILE"

            # Optionally open the image (macOS)
            if command -v open &> /dev/null; then
                echo ""
                read -p "Open image now? (y/n) " -n 1 -r
                echo ""
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    open "$IMAGE_FILE"
                fi
            fi
        fi

        break
    fi

    if [ "$STATUS" == "failed" ]; then
        echo ""
        echo "$STATUS_RESPONSE" | jq .
        echo ""
        echo -e "${YELLOW}❌ Generation failed${NC}"
        exit 1
    fi
done

if [ "$STATUS" != "completed" ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Generation timeout after $MAX_ATTEMPTS attempts${NC}"
    echo "This is normal for CPU-based generation. Check the status later:"
    echo "curl $API_URL/api/status/$JOB_ID | jq ."
fi

echo ""
echo "=============================================="
echo -e "${GREEN}🎉 API test completed!${NC}"
echo ""
echo "Next steps:"
echo "  - View generated images in: generated_images/"
echo "  - Try the API docs: $API_URL/docs"
echo "  - Modify prompts and parameters in this script"
echo ""
