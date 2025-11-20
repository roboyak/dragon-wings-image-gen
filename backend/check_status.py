import httpx
import json
import time

job_id = "83d0d263-2755-4607-9294-940a869f94f3"
url = f"http://localhost:8000/api/status/{job_id}"

print(f"🔍 Checking status for job: {job_id}\n")

for attempt in range(120):  # Check for up to 4 minutes (model download + generation)
    try:
        response = httpx.get(url, timeout=5.0)
        result = response.json()
        
        status = result.get("status")
        print(f"[{attempt+1}] Status: {status}", end="")
        
        if status == "completed":
            print(f"\n\n✅ Image generated successfully!")
            print(f"   Image URL: {result.get('image_url')}")
            print(f"   Generation time: {result.get('generation_time')}s")
            break
        elif status == "failed":
            print(f"\n\n❌ Generation failed!")
            print(f"   Message: {result.get('message')}")
            break
        elif status == "processing":
            print(" - Generating image...")
        else:
            print(" - Queued/pending...")
        
        time.sleep(2)
    except Exception as e:
        print(f"\n⚠️  Error: {e}")
        time.sleep(2)
