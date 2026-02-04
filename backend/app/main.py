"""FastAPI application for Stable Diffusion image generation."""
import os
import uuid
import base64
import logging
import subprocess
from io import BytesIO
from pathlib import Path
from datetime import datetime
from PIL import Image, PngImagePlugin
import piexif
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
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
    InpaintRequest,
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

# Custom StaticFiles with CORS headers for canvas compatibility
class CORSStaticFiles(StaticFiles):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            async def send_with_cors(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((b"access-control-allow-origin", b"*"))
                    headers.append((b"access-control-allow-methods", b"GET, OPTIONS"))
                    headers.append((b"access-control-allow-headers", b"*"))
                    message["headers"] = headers
                await send(message)
            await super().__call__(scope, receive, send_with_cors)
        else:
            await super().__call__(scope, receive, send)

# Mount static files directory for serving generated images
app.mount("/images", CORSStaticFiles(directory=settings.output_dir), name="images")


def add_energy_metadata(image, metadata: dict):
    """
    Add Dragon Wings energy metadata to PNG image.

    Args:
        image: PIL Image object
        metadata: Dict containing energy and generation info

    Returns:
        PngInfo object with embedded metadata
    """
    pnginfo = PngImagePlugin.PngInfo()

    # Dragon Wings custom metadata
    pnginfo.add_text("Dragon-Wings-Unit", metadata.get("unit", "DW1.24"))
    pnginfo.add_text("Generation-Time", f"{metadata.get('generation_time', 0)}s")
    pnginfo.add_text("Energy-Consumption", f"{metadata.get('energy_wh', 0)} Wh")
    pnginfo.add_text("Energy-Source", metadata.get('energy_source', 'Solar'))
    pnginfo.add_text("Generation-Timestamp", metadata.get('timestamp', datetime.utcnow().isoformat()))

    # AI Generation parameters
    pnginfo.add_text("AI-Model", metadata.get('model_key', 'unknown'))
    pnginfo.add_text("AI-Prompt", metadata.get('prompt', ''))
    if metadata.get('negative_prompt'):
        pnginfo.add_text("AI-Negative-Prompt", metadata['negative_prompt'])
    pnginfo.add_text("AI-Steps", str(metadata.get('num_inference_steps', 0)))
    pnginfo.add_text("AI-Guidance", str(metadata.get('guidance_scale', 0)))
    pnginfo.add_text("AI-Seed", str(metadata.get('seed', 'random')))
    pnginfo.add_text("AI-Width", str(metadata.get('width', 512)))
    pnginfo.add_text("AI-Height", str(metadata.get('height', 512)))

    return pnginfo


def add_energy_metadata_jpeg(metadata: dict):
    """
    Add Dragon Wings energy metadata to JPEG image using EXIF.

    Args:
        metadata: Dict containing energy and generation info

    Returns:
        EXIF bytes ready to embed in JPEG
    """
    # Create EXIF data
    exif_dict = {
        "0th": {},
        "Exif": {},
        "GPS": {},
        "1st": {},
        "thumbnail": None,
    }

    # Add Dragon Wings energy data to UserComment (shows in Finder!)
    energy_comment = f"""🌞 Dragon Wings {metadata.get('unit', 'DW1.24')}
⚡ Energy: {metadata.get('energy_wh', 0)} Wh from {metadata.get('energy_source', 'Solar')}
⏱️ Generation: {metadata.get('generation_time', 0)}s
🤖 Model: {metadata.get('model_key', 'unknown')}
📐 Size: {metadata.get('width', 512)}×{metadata.get('height', 512)}
🎨 {metadata.get('prompt', '')[:100]}"""

    exif_dict["Exif"][piexif.ExifIFD.UserComment] = energy_comment.encode('utf-8')

    # Add other standard EXIF fields
    # Make = Energy consumption (shows first in Finder)
    exif_dict["0th"][piexif.ImageIFD.Make] = f"Energy: {metadata.get('energy_wh', 0)} Wh from {metadata.get('energy_source', 'Solar')}".encode('utf-8')
    # Model = Dragon Wings unit ID
    exif_dict["0th"][piexif.ImageIFD.Model] = f"Dragon Wings {metadata.get('unit', 'DW1.24')}".encode('utf-8')
    exif_dict["0th"][piexif.ImageIFD.Software] = f"Dragon Wings AI - {metadata.get('model_key', 'SD')}".encode('utf-8')
    exif_dict["0th"][piexif.ImageIFD.Artist] = "Dragon Wings Solar AI".encode('utf-8')
    exif_dict["0th"][piexif.ImageIFD.Copyright] = f"Generated {datetime.now().year}".encode('utf-8')
    exif_dict["0th"][piexif.ImageIFD.ImageDescription] = metadata.get('prompt', '')[:200].encode('utf-8')

    # Convert to bytes
    exif_bytes = piexif.dump(exif_dict)
    return exif_bytes


def set_finder_comment(filepath: str, metadata: dict):
    """
    Set macOS Finder comment with energy metadata.

    Args:
        filepath: Path to the image file
        metadata: Dict containing energy and generation info
    """
    try:
        # Format comment with energy data
        comment = f"""🌞 Dragon Wings {metadata.get('unit', 'DW1.24')}
⚡ Energy: {metadata.get('energy_wh', 0)} Wh from {metadata.get('energy_source', 'Solar')}
⏱️ Generation: {metadata.get('generation_time', 0)}s
🤖 Model: {metadata.get('model_key', 'unknown')}
📐 Size: {metadata.get('width', 512)}×{metadata.get('height', 512)}
🎨 {metadata.get('prompt', '')[:100]}"""

        # Use osascript to set Finder comment (more reliable than xattr)
        escaped_comment = comment.replace('"', '\\"').replace("'", "\\'")
        escaped_path = filepath.replace('"', '\\"')

        script = f'''tell application "Finder" to set comment of (POSIX file "{escaped_path}" as alias) to "{escaped_comment}"'''

        subprocess.run(['osascript', '-e', script], check=False, capture_output=True)

    except Exception as e:
        # Don't fail the whole generation if comment setting fails
        logger.warning(f"Failed to set Finder comment: {e}")
        pass


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

        # Calculate energy consumption (65W base, adjust for concurrent jobs)
        energy_wh = round((65.0 * (generation_time / 3600.0)), 2)

        # Determine energy source based on time of day
        # TODO: Replace with dragon_minds_os API call
        hour = datetime.now().hour
        energy_source = "Solar" if 6 <= hour < 18 else "Stored Solar"

        # Prepare metadata
        metadata = {
            "unit": "DW1.24",
            "generation_time": round(generation_time, 2),
            "energy_wh": energy_wh,
            "energy_source": energy_source,
            "timestamp": datetime.utcnow().isoformat(),
            "model_key": model_key,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "seed": seed if seed else "random",
            "width": width,
            "height": height,
        }

        # Add energy metadata to PNG
        pnginfo = add_energy_metadata(image, metadata)

        # Save PNG for UI/preview
        filename = f"{job_id}.png"
        filepath = os.path.join(settings.output_dir, filename)
        image.save(filepath, pnginfo=pnginfo)

        # Also save JPEG with EXIF for downloads
        jpeg_filename = f"{job_id}.jpg"
        jpeg_filepath = os.path.join(settings.output_dir, jpeg_filename)

        # Convert to RGB if needed (JPEG doesn't support RGBA)
        jpeg_image = image
        if image.mode in ('RGBA', 'LA', 'P'):
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image_temp = image.convert('RGBA')
            else:
                image_temp = image
            rgb_image.paste(image_temp, mask=image_temp.split()[-1] if image_temp.mode in ('RGBA', 'LA') else None)
            jpeg_image = rgb_image

        # Add EXIF metadata to JPEG
        exif_bytes = add_energy_metadata_jpeg(metadata)
        jpeg_image.save(jpeg_filepath, format="JPEG", quality=95, exif=exif_bytes)

        # Set macOS Finder comment on both files
        set_finder_comment(filepath, metadata)
        set_finder_comment(jpeg_filepath, metadata)

        # Convert to base64 (PNG for preview)
        buffered = BytesIO()
        image.save(buffered, format="PNG", pnginfo=pnginfo)
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

        # Calculate energy consumption (65W base, adjust for concurrent jobs)
        energy_wh = round((65.0 * (generation_time / 3600.0)), 2)

        # Determine energy source based on time of day
        # TODO: Replace with dragon_minds_os API call
        hour = datetime.now().hour
        energy_source = "Solar" if 6 <= hour < 18 else "Stored Solar"

        # Prepare metadata
        metadata = {
            "unit": "DW1.24",
            "generation_time": round(generation_time, 2),
            "energy_wh": energy_wh,
            "energy_source": energy_source,
            "timestamp": datetime.utcnow().isoformat(),
            "model_key": model_key,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "seed": seed if seed else "random",
            "width": width,
            "height": height,
        }

        # Add energy metadata to PNG
        pnginfo = add_energy_metadata(image, metadata)

        # Save PNG for UI/preview
        filename = f"{job_id}.png"
        filepath = os.path.join(settings.output_dir, filename)
        image.save(filepath, pnginfo=pnginfo)

        # Also save JPEG with EXIF for downloads
        jpeg_filename = f"{job_id}.jpg"
        jpeg_filepath = os.path.join(settings.output_dir, jpeg_filename)

        # Convert to RGB if needed (JPEG doesn't support RGBA)
        jpeg_image = image
        if image.mode in ('RGBA', 'LA', 'P'):
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image_temp = image.convert('RGBA')
            else:
                image_temp = image
            rgb_image.paste(image_temp, mask=image_temp.split()[-1] if image_temp.mode in ('RGBA', 'LA') else None)
            jpeg_image = rgb_image

        # Add EXIF metadata to JPEG
        exif_bytes = add_energy_metadata_jpeg(metadata)
        jpeg_image.save(jpeg_filepath, format="JPEG", quality=95, exif=exif_bytes)

        # Set macOS Finder comment on both files
        set_finder_comment(filepath, metadata)
        set_finder_comment(jpeg_filepath, metadata)

        # Convert to base64 (PNG for preview)
        buffered = BytesIO()
        image.save(buffered, format="PNG", pnginfo=pnginfo)
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


def generate_inpaint_task(
    job_id: str,
    init_image: Image.Image,
    mask_image: Image.Image,
    prompt: str,
    model_key: str,
    strength: float,
    negative_prompt: str | None,
    num_inference_steps: int,
    guidance_scale: float,
    seed: int | None,
    blur_mask: bool,
    blur_factor: int,
    lora_specs: list | None = None,
):
    """Background task for inpainting generation."""
    try:
        logger.info(f"Starting inpaint generation for job {job_id} with model {model_key}")
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

        # Generate inpainted image
        image = sd_model.generate_image_inpaint(
            init_image=init_image,
            mask_image=mask_image,
            prompt=prompt,
            model_id=model_id,
            strength=strength,
            negative_prompt=negative_prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
            blur_mask=blur_mask,
            blur_factor=blur_factor,
            progress_callback=update_progress,
            lora_specs=lora_specs,
        )

        generation_time = time.time() - start_time

        # Calculate energy consumption (65W base, adjust for concurrent jobs)
        energy_wh = round((65.0 * (generation_time / 3600.0)), 2)

        # Determine energy source based on time of day
        # TODO: Replace with dragon_minds_os API call
        hour = datetime.now().hour
        energy_source = "Solar" if 6 <= hour < 18 else "Stored Solar"

        # Prepare metadata
        metadata = {
            "unit": "DW1.24",
            "generation_time": round(generation_time, 2),
            "energy_wh": energy_wh,
            "energy_source": energy_source,
            "timestamp": datetime.utcnow().isoformat(),
            "model_key": model_key,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "seed": seed if seed else "random",
            "width": width,
            "height": height,
        }

        # Add energy metadata to PNG
        pnginfo = add_energy_metadata(image, metadata)

        # Save PNG for UI/preview
        filename = f"{job_id}.png"
        filepath = os.path.join(settings.output_dir, filename)
        image.save(filepath, pnginfo=pnginfo)

        # Also save JPEG with EXIF for downloads
        jpeg_filename = f"{job_id}.jpg"
        jpeg_filepath = os.path.join(settings.output_dir, jpeg_filename)

        # Convert to RGB if needed (JPEG doesn't support RGBA)
        jpeg_image = image
        if image.mode in ('RGBA', 'LA', 'P'):
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image_temp = image.convert('RGBA')
            else:
                image_temp = image
            rgb_image.paste(image_temp, mask=image_temp.split()[-1] if image_temp.mode in ('RGBA', 'LA') else None)
            jpeg_image = rgb_image

        # Add EXIF metadata to JPEG
        exif_bytes = add_energy_metadata_jpeg(metadata)
        jpeg_image.save(jpeg_filepath, format="JPEG", quality=95, exif=exif_bytes)

        # Set macOS Finder comment on both files
        set_finder_comment(filepath, metadata)
        set_finder_comment(jpeg_filepath, metadata)

        # Convert to base64 (PNG for preview)
        buffered = BytesIO()
        image.save(buffered, format="PNG", pnginfo=pnginfo)
        image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Update job status
        jobs[job_id].update({
            "status": "completed",
            "image_url": f"/images/{filename}",
            "image_base64": image_base64,
            "generation_time": round(generation_time, 2),
            "message": "Inpaint generated successfully",
            "progress_percent": 100,
        })

        logger.info(f"Inpaint job {job_id} completed in {generation_time:.2f}s")

    except Exception as e:
        logger.error(f"Inpaint job {job_id} failed: {e}")
        jobs[job_id].update({
            "status": "failed",
            "message": f"Inpaint generation failed: {str(e)}",
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


@app.post("/api/generate_inpaint", response_model=GenerateResponse, tags=["Generation"])
async def generate_inpaint(
    init_image: UploadFile = File(..., description="Source image to edit"),
    mask_image: UploadFile = File(..., description="Mask image (white=inpaint, black=preserve)"),
    prompt: str = Form(..., description="Text description of what to paint in masked region"),
    model_key: str = Form("sd-v1-5", description="Model key (sd-v1-5, openjourney, sdxl, etc.)"),
    negative_prompt: str = Form("", description="What to avoid in the image"),
    strength: float = Form(0.8, description="How much to change masked region (0.0-1.0)"),
    num_inference_steps: int = Form(30, description="Number of denoising steps"),
    guidance_scale: float = Form(7.5, description="Prompt adherence strength"),
    seed: int | None = Form(None, description="Random seed for reproducibility"),
    blur_mask: bool = Form(True, description="Whether to blur mask edges"),
    blur_factor: int = Form(33, description="Gaussian blur radius for mask"),
    loras: str | None = Form(None, description="JSON array of LoRA specs [{key, weight}]"),
    background_tasks: BackgroundTasks = None,
):
    """
    Generate an image using inpainting (selective region editing).

    Upload a source image and a mask image. White areas in the mask will be
    regenerated based on the prompt, while black areas are preserved.

    The generation happens asynchronously in the background.
    Use the returned job_id to check status via /api/status/{job_id}.

    Args:
        init_image: Source image file (PNG, JPG, WebP)
        mask_image: Mask image file (white=inpaint, black=preserve)
        prompt: Text description of what to paint in masked region
        model_key: Model to use (must support inpainting)
        negative_prompt: What to avoid in the image
        strength: How much to change masked region (0.0-1.0)
        num_inference_steps: Number of denoising steps (10-100)
        guidance_scale: How closely to follow prompt (1.0-20.0)
        seed: Random seed for reproducibility
        blur_mask: Whether to blur mask edges for smoother blending
        blur_factor: Gaussian blur radius for mask (0-100)
        loras: JSON array of LoRA specs, e.g., '[{"key": "watercolor", "weight": 0.8}]'
    """
    import json

    # Validate model supports inpainting
    if not settings.supports_inpaint(model_key):
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model_key}' does not support inpainting. Use sd-v1-5, openjourney, sdxl, or other SD-based models.",
        )

    # Validate file types
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
    if init_image.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid init_image type. Allowed: {', '.join(allowed_types)}",
        )
    if mask_image.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mask_image type. Allowed: {', '.join(allowed_types)}",
        )

    # Validate strength parameter
    if not (0.0 <= strength <= 1.0):
        raise HTTPException(
            status_code=400,
            detail="Strength must be between 0.0 and 1.0",
        )

    # Validate blur_factor
    if not (0 <= blur_factor <= 100):
        raise HTTPException(
            status_code=400,
            detail="blur_factor must be between 0 and 100",
        )

    # Parse LoRA specs if provided
    lora_specs = None
    if loras:
        try:
            lora_list = json.loads(loras)
            lora_specs = []
            for lora in lora_list:
                lora_key = lora.get("key")
                if not lora_key:
                    continue
                # Check compatibility
                if not settings.is_lora_compatible(lora_key, model_key):
                    compatible_loras = settings.get_compatible_loras(model_key)
                    raise HTTPException(
                        status_code=400,
                        detail=f"LoRA '{lora_key}' is not compatible with model '{model_key}'. Compatible: {', '.join(compatible_loras) if compatible_loras else 'none'}",
                    )
                lora_config = settings.get_lora_config(lora_key)
                weight = lora.get("weight", lora_config["default_weight"])
                lora_specs.append({"key": lora_key, "weight": weight})
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid loras format. Must be valid JSON array.",
            )

    # Read and process uploaded images
    try:
        init_bytes = await init_image.read()
        mask_bytes = await mask_image.read()

        # Validate sizes (max 10MB each)
        max_size_mb = 10
        if len(init_bytes) > max_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"init_image too large. Max size: {max_size_mb}MB",
            )
        if len(mask_bytes) > max_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"mask_image too large. Max size: {max_size_mb}MB",
            )

        init_img = Image.open(BytesIO(init_bytes))
        mask_img = Image.open(BytesIO(mask_bytes))

    except HTTPException:
        raise
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
        "message": "Inpaint job queued for processing",
    }

    # Queue background task
    background_tasks.add_task(
        generate_inpaint_task,
        job_id=job_id,
        init_image=init_img,
        mask_image=mask_img,
        prompt=prompt,
        model_key=model_key,
        strength=strength,
        negative_prompt=negative_prompt if negative_prompt else None,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        seed=seed,
        blur_mask=blur_mask,
        blur_factor=blur_factor,
        lora_specs=lora_specs,
    )

    logger.info(f"Inpaint job {job_id} queued: '{prompt[:50]}...', model={model_key}, strength={strength}, blur={blur_mask}")

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
