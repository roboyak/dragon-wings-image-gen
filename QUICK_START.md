# Quick Start Guide

## Dragon Wings AI Image Generator POC

### Prerequisites

Before you begin, ensure you have:

- **Python 3.10+** installed
- **8GB+ RAM** (16GB+ recommended)
- **~5GB free disk space** (for model and dependencies)
- **GPU optional** (CPU works but slower - 30-60s per image)

### Step 1: Backend Setup (Python FastAPI)

```bash
cd dragon_wings_image_gen/backend

# Run the startup script (handles everything)
./start.sh
```

The startup script will:
1. Create a virtual environment
2. Install all Python dependencies
3. Create `.env` file from template
4. Start the FastAPI server on port 8000

**First run will be slow** - the Stable Diffusion model (~4GB) will download automatically on the first image generation.

### Step 2: Test the API

Open a new terminal and test the API:

```bash
# Health check
curl http://localhost:8000/api/health | jq .

# Should return:
# {
#   "status": "healthy",
#   "model_loaded": false,  # Will be true after first generation
#   "model_id": "runwayml/stable-diffusion-v1-5",
#   "device": "cpu",
#   "version": "1.0.0"
# }
```

### Step 3: Generate Your First Image

```bash
# Generate an image (this will trigger model download on first run)
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A serene landscape with mountains and a lake at sunset",
    "num_inference_steps": 30,
    "guidance_scale": 7.5,
    "width": 512,
    "height": 512
  }' | jq .

# Response will include job_id:
# {
#   "job_id": "abc123...",
#   "status": "pending",
#   "message": "Job queued for processing"
# }
```

### Step 4: Check Generation Status

```bash
# Replace JOB_ID with the job_id from step 3
curl http://localhost:8000/api/status/JOB_ID | jq .

# When completed:
# {
#   "job_id": "abc123...",
#   "status": "completed",
#   "image_url": "/images/abc123.png",
#   "generation_time": 8.5
# }
```

### Step 5: View Generated Image

Images are saved to: `backend/generated_images/`

```bash
# List generated images
ls -lh backend/generated_images/

# Open the image (macOS)
open backend/generated_images/abc123.png

# Or copy to desktop
cp backend/generated_images/abc123.png ~/Desktop/
```

### Step 6: Explore the API Documentation

Visit the interactive API docs:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

You can test all endpoints directly from the browser!

---

## Configuration Options

Edit `backend/.env` to customize:

### Device Selection
```bash
# Use GPU (NVIDIA CUDA)
DEVICE=cuda

# Use CPU (slower but works anywhere)
DEVICE=cpu

# Use Apple Silicon GPU (M1/M2/M3)
DEVICE=mps
```

### Model Selection
```bash
# Faster, smaller model (default)
MODEL_ID=runwayml/stable-diffusion-v1-5

# Better quality, slower, larger
MODEL_ID=stabilityai/stable-diffusion-xl-base-1.0
```

### Performance Tuning
```bash
# Use half-precision (saves memory, requires GPU)
MODEL_PRECISION=fp16

# Increase for better quality (slower)
DEFAULT_STEPS=50

# Default image size
DEFAULT_WIDTH=768
DEFAULT_HEIGHT=768
```

---

## Troubleshooting

### Issue: Model download fails

**Solution:** Check your internet connection. You may need to sign up for a free Hugging Face account and get an access token:

1. Create account at https://huggingface.co/join
2. Get token at https://huggingface.co/settings/tokens
3. Add to `.env`: `HF_TOKEN=your_token_here`

### Issue: Out of memory errors

**Solutions:**
- Reduce image size: `width=384, height=384`
- Use fewer steps: `num_inference_steps=20`
- Close other applications
- Use GPU instead of CPU

### Issue: "CUDA out of memory" on GPU

**Solutions:**
- Use half-precision: `MODEL_PRECISION=fp16` in `.env`
- Reduce image size
- Restart the backend to clear GPU memory

### Issue: Generation is very slow (>60 seconds)

This is normal on CPU. Solutions:
- Use GPU (NVIDIA with CUDA or Apple Silicon)
- Reduce steps: `num_inference_steps=20`
- Use smaller image size: `width=384, height=384`

---

## Example Prompts

### Good Prompts
- "A majestic dragon flying over a medieval castle at sunset, highly detailed, fantasy art"
- "Portrait of a cyberpunk character with neon lights, futuristic, 4k, photorealistic"
- "A cozy coffee shop interior with warm lighting and plants, architectural photography"

### Tips for Better Results
- Be specific and descriptive
- Add quality modifiers: "highly detailed", "4k", "professional photography"
- Use negative prompts to avoid unwanted elements: "blurry, low quality, distorted"
- Experiment with guidance_scale (7-12 works well)
- Use seeds for reproducible results

---

## Next Steps

Once the backend is working:

1. **Build the Rails Frontend** - See `docs/RAILS_SETUP.md`
2. **Add Authentication** - User accounts and image galleries
3. **Add Quota System** - Limit free users to 10 images/day
4. **Deploy to Production** - See `docs/DEPLOYMENT.md`

---

## Getting Help

- **API docs**: http://localhost:8000/docs
- **Check logs**: Backend terminal shows detailed generation logs
- **Test with curl**: See examples above
- **Report issues**: GitHub issues (coming soon)

---

**Ready for production?** See the full README.md for Rails frontend setup and deployment instructions.

🐉 **Happy generating!**
