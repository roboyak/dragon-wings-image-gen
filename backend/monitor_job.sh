#!/bin/bash
JOB_ID=$1
echo "⏳ Monitoring job $JOB_ID..."
echo ""

for i in {1..60}; do
  STATUS=$(curl -s http://localhost:8000/api/status/$JOB_ID | jq -r '.status')
  
  if [ "$STATUS" = "completed" ]; then
    echo ""
    echo "✅ COMPLETED!"
    echo "View at: http://localhost:8000/images/${JOB_ID}.png"
    break
  elif [ "$STATUS" = "failed" ]; then
    echo ""
    echo "❌ FAILED"
    curl -s http://localhost:8000/api/status/$JOB_ID | jq .
    break
  elif [ "$STATUS" = "processing" ]; then
    echo -n "."
  fi
  
  sleep 5
done
