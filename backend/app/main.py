"""FastAPI application for Stable Diffusion image generation."""
import os
import uuid
import base64
import logging
from io import BytesIO
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from .config import settings
from .models import sd_model
from .schemas import (
    GenerateRequest,
    GenerateResponse,
    StatusResponse,
    HealthResponse,
    ErrorResponse,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Job storage (in production, use Redis or database)
jobs = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting up...")

    # Create output directory
    Path(settings.output_dir).mkdir(parents=True, exist_ok=True)

    # Optionally preload model (commented out for faster startup)
    # logger.info("Preloading Stable Diffusion model...")
    # sd_model.load_model()
    # logger.info("Model preloaded")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down...")
    sd_model.unload_model()


# Initialize FastAPI app
app = FastAPI(
    title="Dragon Wings AI Image Generator",
    description="Stable Diffusion image generation API",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for serving generated images
app.mount("/images", StaticFiles(directory=settings.output_dir), name="images")


def generate_image_task(
    job_id: str,
    prompt: str,
    negative_prompt: str | None,
    num_inference_steps: int,
    guidance_scale: float,
    width: int,
    height: int,
    seed: int | None,
):
    """Background task for image generation."""
    try:
        logger.info(f"Starting generation for job {job_id}")
        jobs[job_id]["status"] = "processing"

        import time
        start_time = time.time()

        # Generate image
        image = sd_model.generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            seed=seed,
        )

        generation_time = time.time() - start_time

        # Save image to file
        filename = f"{job_id}.png"
        filepath = os.path.join(settings.output_dir, filename)
        image.save(filepath)

        # Convert to base64
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Update job status
        jobs[job_id].update({
            "status": "completed",
            "image_url": f"/images/{filename}",
            "image_base64": image_base64,
            "generation_time": round(generation_time, 2),
            "message": "Image generated successfully",
        })

        logger.info(f"Job {job_id} completed in {generation_time:.2f}s")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        jobs[job_id].update({
            "status": "failed",
            "message": f"Generation failed: {str(e)}",
        })


@app.get("/", tags=["General"])
async def root():
    """Root endpoint."""
    return {
        "message": "Dragon Wings AI Image Generator API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        model_loaded=sd_model.is_loaded,
        model_id=settings.model_id,
        device=settings.device,
        version="1.0.0",
    )


@app.post("/api/generate", response_model=GenerateResponse, tags=["Generation"])
async def generate_image(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
):
    """
    Generate an image from a text prompt.

    The generation happens asynchronously in the background.
    Use the returned job_id to check status via /api/status/{job_id}.
    """
    # Validate dimensions (must be multiple of 8)
    if request.width % 8 != 0 or request.height % 8 != 0:
        raise HTTPException(
            status_code=400,
            detail="Width and height must be multiples of 8",
        )

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Initialize job status
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "prompt": request.prompt,
        "message": "Job queued for processing",
    }

    # Queue background task
    background_tasks.add_task(
        generate_image_task,
        job_id=job_id,
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        num_inference_steps=request.num_inference_steps,
        guidance_scale=request.guidance_scale,
        width=request.width,
        height=request.height,
        seed=request.seed,
    )

    logger.info(f"Job {job_id} queued: '{request.prompt[:50]}...'")

    return GenerateResponse(**jobs[job_id])


@app.get("/api/status/{job_id}", response_model=StatusResponse, tags=["Generation"])
async def get_status(job_id: str):
    """Check the status of a generation job."""
    if job_id not in jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found",
        )

    job = jobs[job_id]
    return StatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        image_url=job.get("image_url"),
        message=job.get("message"),
        generation_time=job.get("generation_time"),
    )


@app.get("/api/models", tags=["General"])
async def list_models():
    """List available models (placeholder for future multi-model support)."""
    return {
        "current_model": settings.model_id,
        "available_models": [
            {
                "id": "runwayml/stable-diffusion-v1-5",
                "name": "Stable Diffusion 1.5",
                "description": "Fast, balanced quality",
                "size": "~4GB",
            },
            {
                "id": "stabilityai/stable-diffusion-xl-base-1.0",
                "name": "Stable Diffusion XL",
                "description": "Higher quality, slower",
                "size": "~7GB",
            },
        ],
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "detail": str(exc) if settings.debug else None,
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
