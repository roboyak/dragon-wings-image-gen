# Dragon Wings AI Image Generator

## POC: Stable Diffusion SaaS Platform

A Midjourney-style AI image generation platform with Rails frontend and Python backend.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Rails Frontend (Port 3000)                │
│  - User authentication (Devise)                              │
│  - Image generation UI                                       │
│  - Gallery & history                                         │
│  - Real-time status updates (SSE)                            │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST API
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                   Python Backend (Port 8000)                 │
│  - FastAPI REST API                                          │
│  - Stable Diffusion model                                    │
│  - Image generation processing                               │
│  - Async task handling                                       │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Backend
- **Python 3.10+**
- **FastAPI** - Modern async web framework
- **Stable Diffusion** (via Hugging Face `diffusers`)
- **PyTorch** - Deep learning framework
- **Pillow** - Image processing

### Frontend
- **Ruby on Rails 7**
- **Hotwire/Turbo** - Real-time updates
- **Devise** - Authentication
- **ActiveStorage** - Image storage
- **Tailwind CSS** - Dark theme UI

## Project Structure

```
dragon_wings_image_gen/
├── backend/                 # Python FastAPI application
│   ├── app/
│   │   ├── main.py         # FastAPI app entry point
│   │   ├── models.py       # Stable Diffusion model loader
│   │   ├── api/            # API routes
│   │   │   ├── generate.py # Image generation endpoint
│   │   │   └── health.py   # Health check endpoint
│   │   └── utils.py        # Helper functions
│   ├── tests/              # Backend tests
│   ├── requirements.txt    # Python dependencies
│   ├── .env.example        # Environment variables template
│   └── Dockerfile          # Docker container config
│
├── frontend/               # Rails application
│   ├── app/
│   │   ├── controllers/    # Rails controllers
│   │   ├── models/         # Rails models (User, Image)
│   │   ├── views/          # Rails views
│   │   └── services/       # API client service
│   ├── config/             # Rails configuration
│   ├── db/                 # Database migrations
│   └── Gemfile             # Ruby dependencies
│
└── README.md               # This file
```

## Features (POC)

### Core Features
- ✅ Text-to-image generation
- ✅ Image gallery with history
- ✅ User authentication
- ✅ Generation parameters (steps, guidance, seed)
- ✅ Real-time generation status
- ✅ Image download

### User Management
- ✅ Free tier: 10 images/day
- ✅ Pro tier: 100 images/day
- ✅ Quota tracking

### Image Parameters
- Prompt (text description)
- Negative prompt (what to avoid)
- Steps (quality vs speed: 20-50)
- Guidance scale (prompt adherence: 7-12)
- Seed (reproducibility)
- Size (512x512, 768x768, 1024x1024)

## Quick Start

### Prerequisites
- Python 3.10+ with pip
- Ruby 3.1+ with Rails 7
- PostgreSQL 12+
- CUDA-capable GPU (recommended) or CPU (slower, ~2-3 minutes per image)
- 8GB+ RAM (16GB+ recommended)
- 10GB+ disk space (for model files)

### 🚀 Start the System (Both Services)

#### 1. Start Python Backend (Port 8000)

```bash
cd backend

# First time setup
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start the backend (keep this terminal open)
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# ✅ Backend ready when you see:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Application startup complete.
```

**Backend URLs:**
- API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- Health Check: http://localhost:8000/api/health

#### 2. Start Rails Frontend (Port 3000)

Open a **new terminal window**:

```bash
cd frontend

# First time setup
bundle install
bin/rails db:create
bin/rails db:migrate

# Create test user (optional)
bin/rails runner "User.create!(email: 'admin@dragonwings.ai', password: 'dragonwings123', password_confirmation: 'dragonwings123', subscription_tier: :enterprise); puts 'Test user created: admin@dragonwings.ai / dragonwings123'"

# Start the frontend (keep this terminal open)
bin/rails server -p 3000

# ✅ Frontend ready when you see:
# Listening on http://0.0.0.0:3000
# Use Ctrl-C to stop
```

**Frontend URL:**
- App: http://localhost:3000
- Login: http://localhost:3000/users/sign_in

#### 3. Access the Application

1. Open http://localhost:3000 in your browser
2. Sign in with test credentials:
   - **Email:** `admin@dragonwings.ai`
   - **Password:** `dragonwings123`
3. Click "AI Image Generation" or navigate to http://localhost:3000/images
4. Enter a prompt (e.g., "A majestic dragon soaring through storm clouds, digital art")
5. Click "Generate Image"
6. Wait 30-180 seconds (CPU) or 5-15 seconds (GPU)
7. Image will appear in the gallery automatically!

### ⚡ Quick Commands

**Start both services:**
```bash
# Terminal 1 - Backend
cd backend && source venv/bin/activate && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend && bin/rails server -p 3000
```

**Stop services:**
Press `Ctrl+C` in each terminal

**Check if services are running:**
```bash
# Backend health check
curl http://localhost:8000/api/health

# Frontend check
curl http://localhost:3000
```

### 📝 Notes

- **First generation:** The first image generation will download the Stable Diffusion model (~4GB). This only happens once and takes 5-10 minutes.
- **Generation time:** CPU: 30-180 seconds per image | GPU (CUDA): 5-15 seconds per image
- **Quota system:** Enterprise tier = 1000 images/day, Pro = 200/day, Maker = 50/day, Free = 10/day
- **Database:** Uses SQLite by default for easy setup. PostgreSQL recommended for production.
- **Static files:** Generated images are served from `backend/generated_images/` via Python backend on port 8000

## API Endpoints

### Backend (Python)

```
POST   /api/generate       # Generate image from prompt
GET    /api/status/:job_id # Check generation status
GET    /api/models         # List available models
GET    /api/health         # Health check
```

### Frontend (Rails)

```
GET    /                   # Home page
POST   /users/sign_in      # Login
POST   /users/sign_up      # Register
GET    /images             # Gallery
POST   /images/generate    # Create generation job
GET    /images/:id         # View image details
```

## Development Workflow

Following the incremental development methodology from Dragon Wings AI:

### Phase 1: Backend Foundation
1. Initialize FastAPI app
2. Add Stable Diffusion integration
3. Test API endpoints

### Phase 2: Frontend Foundation
1. Initialize Rails app
2. Add authentication (Devise)
3. Create image generation form
4. Integrate with Python API
5. Add image storage
6. Build gallery

### Phase 3: Real-time Features
1. Add Server-Sent Events for status
2. Add progress indicators
3. Add queue management

### Phase 4: Polish & Deploy
1. Add user quota system
2. Add error handling
3. Add tests
4. Deployment documentation

## Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
bin/rails test
bin/rails test:system
```

## Deployment

### Docker Compose (Recommended)

```bash
docker-compose up -d
```

This will start:
- Python backend on port 8000
- Rails frontend on port 3000
- PostgreSQL database on port 5432

### Manual Deployment

See `docs/DEPLOYMENT.md` for detailed deployment instructions.

## Performance Notes

- **GPU recommended:** CPU generation takes 30-60 seconds per image
- **GPU (CUDA):** 3-10 seconds per image
- **Model size:** ~4GB for SD 1.5, ~7GB for SDXL
- **RAM:** 8GB minimum, 16GB+ recommended

## Troubleshooting

### Common Issues

**Issue:** Python backend fails to start
**Fix:** Ensure PyTorch is installed correctly for your system (CUDA/CPU)

**Issue:** Model download fails
**Fix:** Check internet connection, Hugging Face may require login for some models

**Issue:** Rails can't connect to Python API
**Fix:** Verify `PYTHON_API_URL` in frontend `.env` file

**Issue:** Out of memory errors
**Fix:** Reduce image size or use lower precision (fp16)

See `docs/TROUBLESHOOTING.md` for more details.

## Roadmap

### MVP (Current POC) ✅ COMPLETE!
- [x] Architecture planning
- [x] Python backend with Stable Diffusion
- [x] Rails frontend with authentication (Devise)
- [x] Image generation form with parameters
- [x] Real-time status polling
- [x] Image gallery with history
- [x] User quota system (4 tiers)
- [x] Dark theme UI (Dragon Wings branding)
- [x] End-to-end tested and working!

### Future Features
- [ ] Image-to-image generation
- [ ] Inpainting (edit specific areas)
- [ ] Multiple models (SD 1.5, SDXL, custom)
- [ ] Batch generation
- [ ] Private/public gallery
- [ ] Social features (likes, comments)
- [ ] API access for developers
- [ ] Subscription payment integration

## License

[To be determined]

## Credits

- Stable Diffusion by Stability AI
- Built following Dragon Wings incremental development methodology
- Inspired by Midjourney

## Support

For issues and questions, please open a GitHub issue.

---

**Status:** ✅ POC Complete & Working!
**Last Updated:** 2025-11-20
**Tested:** End-to-end image generation verified
**Performance:** ~145 seconds per 512x512 image on Apple M1 CPU
