# Dragon Wings Image Generator - Startup Guide

## Quick Start

### Start Both Services
```bash
# Terminal 1: Backend (FastAPI + Stable Diffusion)
cd dragon_wings_image_gen/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend (Rails)
cd dragon_wings_image_gen/frontend
bin/rails s -p 3000
```

### Access the App
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

---

## Service Details

### Backend (Python/FastAPI)
**Port:** 8000
**Location:** `dragon_wings_image_gen/backend/`

```bash
# Start
cd dragon_wings_image_gen/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Start in background
uvicorn app.main:app --reload --port 8000 &

# Check health
curl http://localhost:8000/api/health

# Stop
pkill -f "uvicorn app.main:app"
# or
kill $(lsof -t -i:8000)
```

### Frontend (Ruby on Rails)
**Port:** 3000
**Location:** `dragon_wings_image_gen/frontend/`

```bash
# Start
cd dragon_wings_image_gen/frontend
bin/rails s -p 3000

# Start in background (daemon mode)
bin/rails s -d -p 3000

# Stop
bin/rails s -d -p 3000 --stop
# or
kill $(lsof -t -i:3000)
```

---

## Environment Configuration

### Backend `.env`
```bash
# GPU Acceleration (M-series Mac)
DEVICE=mps
MODEL_PRECISION=fp16

# CPU Mode (slower, but works everywhere)
# DEVICE=cpu
# MODEL_PRECISION=fp32

# Hugging Face token for model downloads
HF_TOKEN=your_token_here
```

### Performance Notes
| Mode | First Step | Total (30 steps) |
|------|------------|------------------|
| CPU (fp32) | ~60-70s | ~30 min |
| MPS (fp16) | ~3-5s | ~2-3 min |
| CUDA (fp16) | ~1-2s | ~30-60s |

---

## Troubleshooting

### Port Already in Use
```bash
# Find and kill process on port
lsof -i :3000  # or :8000
kill -9 <PID>
```

### Backend Not Responding
```bash
# Check if running
curl http://localhost:8000/api/health

# Check logs
tail -f /tmp/backend.log
```

### Model Loading Issues
```bash
# Clear Hugging Face cache if corrupted
rm -rf ~/.cache/huggingface/hub/models--runwayml--stable-diffusion-v1-5
```

---

## Stop All Services

```bash
# Stop both services
pkill -f "uvicorn app.main:app"
pkill -f "puma.*dragon_wings"
# or
kill $(lsof -t -i:3000) $(lsof -t -i:8000) 2>/dev/null
```

---

## Logs

```bash
# Backend logs (if redirected)
tail -f /tmp/backend.log

# Rails logs
tail -f dragon_wings_image_gen/frontend/log/development.log
```
