"""FastAPI application for Stable Diffusion image generation."""
import os
import uuid
import base64
import logging
from io import BytesIO
from pathlib import Path
from PIL import Image
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from .config import settings, MODEL_CONFIGS, LORA_CONFIGS
from .models import sd_model
from .schemas import (
    GenerateRequest,
    GenerateResponse,
    StatusResponse,
    HealthResponse,
    ErrorResponse,
    Img2ImgRequest,
    LoraSpec,
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
    model_key: str,
    negative_prompt: str | None,
    num_inference_steps: int,
    guidance_scale: float,
    width: int,
    height: int,
    seed: int | None,
    lora_specs: list | None = None,
):
    """Background task for image generation."""
    try:
        logger.info(f"Starting generation for job {job_id} with model {model_key}")
        if lora_specs:
            logger.info(f"  LoRAs: {lora_specs}")
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress_percent"] = 0

        import time
        start_time = time.time()

        # Convert model_key to model_id
        model_id = settings.get_model_id_from_key(model_key)

        # Progress callback to update job status
        def update_progress(progress: float):
            jobs[job_id]["progress_percent"] = round(progress, 1)

        # Generate image
        image = sd_model.generate_image(
            prompt=prompt,
            model_id=model_id,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            seed=seed,
            progress_callback=update_progress,
            lora_specs=lora_specs,
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
            "progress_percent": 100,
        })

        logger.info(f"Job {job_id} completed in {generation_time:.2f}s")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        jobs[job_id].update({
            "status": "failed",
            "message": f"Generation failed: {str(e)}",
        })


def generate_img2img_task(
    job_id: str,
    init_image: Image.Image,
    prompt: str,
    model_key: str,
    strength: float,
    negative_prompt: str | None,
    num_inference_steps: int,
    guidance_scale: float,
    seed: int | None,
):
    """Background task for img2img generation."""
    try:
        logger.info(f"Starting img2img generation for job {job_id} with model {model_key}")
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress_percent"] = 0

        import time
        start_time = time.time()

        # Convert model_key to model_id
        model_id = settings.get_model_id_from_key(model_key)

        # Progress callback to update job status
        def update_progress(progress: float):
            jobs[job_id]["progress_percent"] = round(progress, 1)

        # Generate image from image
        image = sd_model.generate_image_from_image(
            init_image=init_image,
            prompt=prompt,
            model_id=model_id,
            strength=strength,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
            progress_callback=update_progress,
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
            "message": "Img2img generated successfully",
            "progress_percent": 100,
        })

        logger.info(f"Img2img job {job_id} completed in {generation_time:.2f}s")

    except Exception as e:
        logger.error(f"Img2img job {job_id} failed: {e}")
        jobs[job_id].update({
            "status": "failed",
            "message": f"Img2img generation failed: {str(e)}",
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

    # Validate LoRA compatibility and convert to lora_specs format
    lora_specs = None
    if request.loras:
        lora_specs = []
        for lora in request.loras:
            # Check if LoRA exists
            if not settings.is_lora_compatible(lora.key, request.model_key):
                compatible_loras = settings.get_compatible_loras(request.model_key)
                raise HTTPException(
                    status_code=400,
                    detail=f"LoRA '{lora.key}' is not compatible with model '{request.model_key}'. Compatible LoRAs: {', '.join(compatible_loras) if compatible_loras else 'none'}",
                )

            # Get LoRA config and use weight or default
            lora_config = settings.get_lora_config(lora.key)
            weight = lora.weight if lora.weight is not None else lora_config["default_weight"]

            lora_specs.append({
                "key": lora.key,
                "weight": weight,
            })

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
        model_key=request.model_key,
        negative_prompt=request.negative_prompt,
        num_inference_steps=request.num_inference_steps,
        guidance_scale=request.guidance_scale,
        width=request.width,
        height=request.height,
        seed=request.seed,
        lora_specs=lora_specs,
    )

    logger.info(f"Job {job_id} queued: '{request.prompt[:50]}...' (model: {request.model_key})")

    return GenerateResponse(**jobs[job_id])


@app.post("/api/generate_img2img", response_model=GenerateResponse, tags=["Generation"])
async def generate_img2img(
    init_image: UploadFile = File(...),
    prompt: str = Form(...),
    model_key: str = Form("sd-v1-5"),
    negative_prompt: str = Form(""),
    strength: float = Form(0.75),
    num_inference_steps: int = Form(50),
    guidance_scale: float = Form(7.5),
    seed: int | None = Form(None),
    background_tasks: BackgroundTasks = None,
):
    """
    Generate an image from an initial image and text prompt (img2img).

    The generation happens asynchronously in the background.
    Use the returned job_id to check status via /api/status/{job_id}.

    Args:
        init_image: Initial image file (PNG, JPG, WebP)
        prompt: Text description of desired transformation
        negative_prompt: What to avoid in the image
        strength: Transformation strength (0.0=keep original, 1.0=complete transform)
        num_inference_steps: Number of denoising steps (10-100)
        guidance_scale: How closely to follow prompt (1.0-20.0)
        seed: Random seed for reproducibility
    """
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
    if init_image.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image type. Allowed: {', '.join(allowed_types)}",
        )

    # Validate strength parameter
    if not (0.0 <= strength <= 1.0):
        raise HTTPException(
            status_code=400,
            detail="Strength must be between 0.0 and 1.0",
        )

    # Read and process uploaded image
    try:
        image_bytes = await init_image.read()
        init_img = Image.open(BytesIO(image_bytes))

        # Validate image size (max 10MB)
        max_size_mb = 10
        if len(image_bytes) > max_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"Image too large. Max size: {max_size_mb}MB",
            )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image file: {str(e)}",
        )

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Initialize job status
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "prompt": prompt,
        "message": "Img2img job queued for processing",
    }

    # Queue background task
    background_tasks.add_task(
        generate_img2img_task,
        job_id=job_id,
        init_image=init_img,
        prompt=prompt,
        model_key=model_key,
        strength=strength,
        negative_prompt=negative_prompt if negative_prompt else None,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        seed=seed,
    )

    logger.info(f"Img2img job {job_id} queued: '{prompt[:50]}...', model={model_key}, strength={strength}")

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
        progress_percent=job.get("progress_percent"),
    )


@app.get("/api/loras", tags=["LoRA"])
async def list_loras(model_key: str | None = None):
    """
    List available LoRA adapters.

    Args:
        model_key: Optional model key to filter LoRAs by compatibility

    Returns:
        List of LoRA configurations, optionally filtered by model compatibility
    """
    loras_with_keys = {}

    for key, config in LORA_CONFIGS.items():
        # Filter by model compatibility if model_key is provided
        if model_key is not None:
            if not settings.is_lora_compatible(key, model_key):
                continue

        loras_with_keys[key] = {
            "key": key,
            **config
        }

    return {
        "filter_model": model_key,
        "count": len(loras_with_keys),
        "loras": loras_with_keys,
    }


@app.get("/api/loras/{lora_key}", tags=["LoRA"])
async def get_lora(lora_key: str):
    """
    Get details for a specific LoRA adapter.

    Args:
        lora_key: The LoRA identifier (e.g., 'thangka', 'watercolor')

    Returns:
        LoRA configuration details

    Raises:
        404: If LoRA not found
    """
    if lora_key not in LORA_CONFIGS:
        raise HTTPException(
            status_code=404,
            detail=f"LoRA '{lora_key}' not found. Available: {', '.join(LORA_CONFIGS.keys())}",
        )

    config = LORA_CONFIGS[lora_key]
    return {
        "key": lora_key,
        **config
    }


@app.get("/api/models", tags=["General"])
async def list_models():
    """List available Stable Diffusion models with detailed metadata."""
    # Add model key to each config, filtering out GPU-only models when on CPU
    has_gpu = settings.device in ["cuda", "mps"]
    models_with_keys = {}
    for key, config in MODEL_CONFIGS.items():
        # Skip GPU-required models when running on CPU
        if config.get("requires_gpu", False) and not has_gpu:
            continue
        models_with_keys[key] = {
            "key": key,
            **config
        }

    return {
        "current_model_id": settings.model_id,
        "default_model_key": "sd-v1-5",
        "device": settings.device,
        "has_gpu": has_gpu,
        "models": models_with_keys,
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
