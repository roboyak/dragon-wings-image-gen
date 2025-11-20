import httpx
import json

url = "http://localhost:8000/api/generate"
data = {
    "prompt": "A serene mountain landscape at sunset with a lake, highly detailed, 4k",
    "negative_prompt": "blurry, low quality, distorted",
    "num_inference_steps": 25,
    "guidance_scale": 7.5,
    "width": 512,
    "height": 512,
    "seed": 42
}

print("🚀 Submitting image generation request...")
response = httpx.post(url, json=data, timeout=10.0)
result = response.json()
print(json.dumps(result, indent=2))

job_id = result.get("job_id")
if job_id:
    print(f"\n✅ Job submitted! Job ID: {job_id}")
    print(f"   Status: {result.get('status')}")
    print(f"   Message: {result.get('message')}")
