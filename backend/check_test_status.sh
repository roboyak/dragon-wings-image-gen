#!/bin/bash

echo "📊 Checking status of all test variations..."
echo "=============================================="
echo ""

JOB_COUNT=1
while IFS= read -r job_id; do
  STATUS=$(curl -s http://localhost:8000/api/status/$job_id | jq -r '.status')
  IMAGE_URL=$(curl -s http://localhost:8000/api/status/$job_id | jq -r '.image_url')

  echo "Test $JOB_COUNT: $job_id"
  echo "   Status: $STATUS"
  if [ "$IMAGE_URL" != "null" ]; then
    echo "   ✅ Image: http://localhost:8000$IMAGE_URL"
  fi
  echo ""

  JOB_COUNT=$((JOB_COUNT + 1))
done < /tmp/img2img_test_jobs.txt

echo "=============================================="
echo ""
echo "Parameter Matrix:"
echo "Test 1: strength=0.30, guidance=7.5, steps=50 (Very Subtle)"
echo "Test 2: strength=0.45, guidance=7.5, steps=50 (Balanced)"
echo "Test 3: strength=0.50, guidance=7.5, steps=50 (Moderate)"
echo "Test 4: strength=0.40, guidance=10,  steps=50 (High Guidance)"
echo "Test 5: strength=0.35, guidance=8,   steps=75 (More Steps)"
echo "Test 6: strength=0.25, guidance=7.5, steps=60 (Max Preservation)"
