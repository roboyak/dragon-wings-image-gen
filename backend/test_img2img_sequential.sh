#!/bin/bash

# Test img2img sequentially (one at a time) to avoid concurrency issues

IMAGE_PATH="/Users/roboyak/0_DragonWings/src/test_images/Dragon+Wings+Solar+Generator+Angle+Hero.jpg"
PROMPT="Add a Vincent Van Gogh effect to the dragon wings portable solar powered generator"
NEGATIVE_PROMPT="blurry, low quality, distorted, deformed"

echo "🎨 Generating img2img variations SEQUENTIALLY..."
echo "================================================"
echo ""

# Function to wait for job completion
wait_for_job() {
    local job_id=$1
    local test_name=$2

    echo "⏳ Waiting for $test_name to complete..."

    while true; do
        status=$(curl -s http://localhost:8000/api/status/$job_id | jq -r '.status')

        if [ "$status" = "completed" ]; then
            echo "✅ $test_name COMPLETED"
            echo "   View: http://localhost:8000/images/${job_id}.png"
            echo ""
            break
        elif [ "$status" = "failed" ]; then
            echo "❌ $test_name FAILED"
            echo ""
            break
        elif [ "$status" = "processing" ]; then
            echo -n "."
            sleep 5
        else
            sleep 2
        fi
    done
}

# Test 1: Very Subtle (0.25)
echo "Test 1: Maximum preservation (strength=0.25, guidance=7.5, steps=60)"
JOB1=$(curl -s -X POST http://localhost:8000/api/generate_img2img \
  -F "init_image=@${IMAGE_PATH}" \
  -F "prompt=${PROMPT}" \
  -F "negative_prompt=${NEGATIVE_PROMPT}" \
  -F "strength=0.25" \
  -F "num_inference_steps=60" \
  -F "guidance_scale=7.5" | jq -r '.job_id')
echo "   Job ID: $JOB1"
wait_for_job "$JOB1" "Test 1 (strength=0.25)"

# Test 2: Subtle (0.3)
echo "Test 2: Very subtle style transfer (strength=0.3, guidance=7.5, steps=50)"
JOB2=$(curl -s -X POST http://localhost:8000/api/generate_img2img \
  -F "init_image=@${IMAGE_PATH}" \
  -F "prompt=${PROMPT}" \
  -F "negative_prompt=${NEGATIVE_PROMPT}" \
  -F "strength=0.3" \
  -F "num_inference_steps=50" \
  -F "guidance_scale=7.5" | jq -r '.job_id')
echo "   Job ID: $JOB2"
wait_for_job "$JOB2" "Test 2 (strength=0.3)"

# Test 3: Subtle with quality (0.35)
echo "Test 3: Subtle + high quality (strength=0.35, guidance=8, steps=75)"
JOB3=$(curl -s -X POST http://localhost:8000/api/generate_img2img \
  -F "init_image=@${IMAGE_PATH}" \
  -F "prompt=${PROMPT}" \
  -F "negative_prompt=${NEGATIVE_PROMPT}" \
  -F "strength=0.35" \
  -F "num_inference_steps=75" \
  -F "guidance_scale=8" | jq -r '.job_id')
echo "   Job ID: $JOB3"
wait_for_job "$JOB3" "Test 3 (strength=0.35)"

# Test 4: Balanced with high guidance (0.4)
echo "Test 4: Balanced + high guidance (strength=0.4, guidance=10, steps=50)"
JOB4=$(curl -s -X POST http://localhost:8000/api/generate_img2img \
  -F "init_image=@${IMAGE_PATH}" \
  -F "prompt=${PROMPT}" \
  -F "negative_prompt=${NEGATIVE_PROMPT}" \
  -F "strength=0.4" \
  -F "num_inference_steps=50" \
  -F "guidance_scale=10" | jq -r '.job_id')
echo "   Job ID: $JOB4"
wait_for_job "$JOB4" "Test 4 (strength=0.4)"

# Test 5: Balanced (0.45)
echo "Test 5: Balanced transformation (strength=0.45, guidance=7.5, steps=50)"
JOB5=$(curl -s -X POST http://localhost:8000/api/generate_img2img \
  -F "init_image=@${IMAGE_PATH}" \
  -F "prompt=${PROMPT}" \
  -F "negative_prompt=${NEGATIVE_PROMPT}" \
  -F "strength=0.45" \
  -F "num_inference_steps=50" \
  -F "guidance_scale=7.5" | jq -r '.job_id')
echo "   Job ID: $JOB5"
wait_for_job "$JOB5" "Test 5 (strength=0.45)"

# Test 6: Moderate (0.5) - already completed earlier
echo "Test 6: Moderate (strength=0.5) - ALREADY COMPLETED"
echo "   Job ID: 8c7adc2e-ed99-4188-b0d0-64635c942197"
echo "   View: http://localhost:8000/images/8c7adc2e-ed99-4188-b0d0-64635c942197.png"
echo ""

echo "================================================"
echo "✅ All 6 variations complete!"
echo ""
echo "📊 Summary:"
echo "Test 1 (0.25): http://localhost:8000/images/${JOB1}.png"
echo "Test 2 (0.30): http://localhost:8000/images/${JOB2}.png"
echo "Test 3 (0.35): http://localhost:8000/images/${JOB3}.png"
echo "Test 4 (0.40): http://localhost:8000/images/${JOB4}.png"
echo "Test 5 (0.45): http://localhost:8000/images/${JOB5}.png"
echo "Test 6 (0.50): http://localhost:8000/images/8c7adc2e-ed99-4188-b0d0-64635c942197.png"
echo ""
echo "Compare them and tell me which strength value gives the best result!"
