#!/bin/bash

# Test img2img with different parameter variations
# Testing strength and guidance_scale for optimal Van Gogh style transfer

IMAGE_PATH="/Users/roboyak/0_DragonWings/src/test_images/Dragon+Wings+Solar+Generator+Angle+Hero.jpg"
PROMPT="Add a Vincent Van Gogh effect to the dragon wings portable solar powered generator"
NEGATIVE_PROMPT="blurry, low quality, distorted, deformed"

echo "🎨 Generating img2img variations..."
echo "=================================="
echo ""

# Test 1: Very subtle (Midjourney-like preservation)
echo "Test 1: Subtle style transfer (strength=0.3, guidance=7.5, steps=50)"
JOB1=$(curl -s -X POST http://localhost:8000/api/generate_img2img \
  -F "init_image=@${IMAGE_PATH}" \
  -F "prompt=${PROMPT}" \
  -F "negative_prompt=${NEGATIVE_PROMPT}" \
  -F "strength=0.3" \
  -F "num_inference_steps=50" \
  -F "guidance_scale=7.5" | jq -r '.job_id')
echo "   Job ID: $JOB1"
echo ""

# Test 2: Balanced (recommended default)
echo "Test 2: Balanced transformation (strength=0.45, guidance=7.5, steps=50)"
JOB2=$(curl -s -X POST http://localhost:8000/api/generate_img2img \
  -F "init_image=@${IMAGE_PATH}" \
  -F "prompt=${PROMPT}" \
  -F "negative_prompt=${NEGATIVE_PROMPT}" \
  -F "strength=0.45" \
  -F "num_inference_steps=50" \
  -F "guidance_scale=7.5" | jq -r '.job_id')
echo "   Job ID: $JOB2"
echo ""

# Test 3: Moderate (current default)
echo "Test 3: Moderate transformation (strength=0.5, guidance=7.5, steps=50)"
JOB3=$(curl -s -X POST http://localhost:8000/api/generate_img2img \
  -F "init_image=@${IMAGE_PATH}" \
  -F "prompt=${PROMPT}" \
  -F "negative_prompt=${NEGATIVE_PROMPT}" \
  -F "strength=0.5" \
  -F "num_inference_steps=50" \
  -F "guidance_scale=7.5" | jq -r '.job_id')
echo "   Job ID: $JOB3"
echo ""

# Test 4: Balanced with higher guidance (more prompt adherence)
echo "Test 4: Balanced + high guidance (strength=0.4, guidance=10, steps=50)"
JOB4=$(curl -s -X POST http://localhost:8000/api/generate_img2img \
  -F "init_image=@${IMAGE_PATH}" \
  -F "prompt=${PROMPT}" \
  -F "negative_prompt=${NEGATIVE_PROMPT}" \
  -F "strength=0.4" \
  -F "num_inference_steps=50" \
  -F "guidance_scale=10" | jq -r '.job_id')
echo "   Job ID: $JOB4"
echo ""

# Test 5: Subtle with more steps (better quality)
echo "Test 5: Subtle + more steps (strength=0.35, guidance=8, steps=75)"
JOB5=$(curl -s -X POST http://localhost:8000/api/generate_img2img \
  -F "init_image=@${IMAGE_PATH}" \
  -F "prompt=${PROMPT}" \
  -F "negative_prompt=${NEGATIVE_PROMPT}" \
  -F "strength=0.35" \
  -F "num_inference_steps=75" \
  -F "guidance_scale=8" | jq -r '.job_id')
echo "   Job ID: $JOB5"
echo ""

# Test 6: Very subtle (maximum preservation)
echo "Test 6: Maximum preservation (strength=0.25, guidance=7.5, steps=60)"
JOB6=$(curl -s -X POST http://localhost:8000/api/generate_img2img \
  -F "init_image=@${IMAGE_PATH}" \
  -F "prompt=${PROMPT}" \
  -F "negative_prompt=${NEGATIVE_PROMPT}" \
  -F "strength=0.25" \
  -F "num_inference_steps=60" \
  -F "guidance_scale=7.5" | jq -r '.job_id')
echo "   Job ID: $JOB6"
echo ""

echo "=================================="
echo "✅ All 6 variations queued!"
echo ""
echo "Job IDs saved for status checking..."
echo "$JOB1" > /tmp/img2img_test_jobs.txt
echo "$JOB2" >> /tmp/img2img_test_jobs.txt
echo "$JOB3" >> /tmp/img2img_test_jobs.txt
echo "$JOB4" >> /tmp/img2img_test_jobs.txt
echo "$JOB5" >> /tmp/img2img_test_jobs.txt
echo "$JOB6" >> /tmp/img2img_test_jobs.txt
echo ""
echo "📊 Check status with:"
echo "   curl http://localhost:8000/api/status/<JOB_ID> | jq ."
echo ""
echo "🖼️  View results at:"
echo "   http://localhost:8000/images/<JOB_ID>.png"
