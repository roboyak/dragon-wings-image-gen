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
- Ruby 3.2+ with Rails 7
- PostgreSQL
- CUDA-capable GPU (recommended) or CPU (slower)
- 8GB+ RAM (16GB+ recommended)

### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download Stable Diffusion model (first run only, ~4GB)
# Model will auto-download on first generation

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run FastAPI server
uvicorn app.main:app --reload --port 8000
```

Backend will be available at: `http://localhost:8000`
API docs (Swagger): `http://localhost:8000/docs`

### Frontend Setup

```bash
cd frontend

# Install Ruby dependencies
bundle install

# Setup database
bin/rails db:create
bin/rails db:migrate
bin/rails db:seed

# Set environment variables
cp .env.example .env
# Edit .env with your configuration
# Set PYTHON_API_URL=http://localhost:8000

# Run Rails server
bin/rails server
```

Frontend will be available at: `http://localhost:3000`

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

### MVP (Current POC)
- [x] Architecture planning
- [ ] Python backend with Stable Diffusion
- [ ] Rails frontend with authentication
- [ ] Image generation and gallery
- [ ] Basic quota system

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

**Status:** 🚧 POC in development
**Last Updated:** 2025-11-20
