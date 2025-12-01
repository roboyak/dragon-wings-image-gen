"""Stable Diffusion model management."""
import os
import logging
from typing import Optional
from PIL import Image
import torch

# Default negative prompt for quality improvement
# This catches common SD artifacts and quality issues
DEFAULT_NEGATIVE_PROMPT = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, "
    "fewer digits, cropped, worst quality, low quality, normal quality, "
    "jpeg artifacts, signature, watermark, username, blurry, deformed, "
    "disfigured, mutation, mutated, ugly, duplicate, morbid, mutilated, "
    "out of frame, extra limbs, bad proportions, malformed limbs, missing arms, "
    "missing legs, extra arms, extra legs, fused fingers, too many fingers, "
    "long neck, poorly drawn hands, poorly drawn face"
)

# Fix for MPS black image bug on Apple Silicon
if torch.backends.mps.is_available():
    torch.backends.mps.enable_fallback_operations = True

from diffusers import (
    StableDiffusionPipeline,
    StableDiffusionImg2ImgPipeline,
    StableDiffusionXLPipeline,
    StableDiffusionXLImg2ImgPipeline,
    DPMSolverMultistepScheduler,
)
from .config import settings

logger = logging.getLogger(__name__)


class StableDiffusionModel:
    """Manages the Stable Diffusion model lifecycle with multi-model support."""

    # SDXL model identifiers
    SDXL_MODEL_IDS = [
        "stabilityai/stable-diffusion-xl-base-1.0",
        "stabilityai/stable-diffusion-xl-refiner-1.0",
    ]

    def __init__(self):
        # Cache for loaded models: {model_id: {"txt2img": pipe, "img2img": pipe}}
        self.model_cache = {}
        self.device = settings.device
        self.current_model_id = settings.model_id

    def _is_sdxl_model(self, model_id: str) -> bool:
        """Check if the model is an SDXL model."""
        return any(sdxl_id in model_id for sdxl_id in self.SDXL_MODEL_IDS)

    def load_model(self, model_id: str = None):
        """Load the Stable Diffusion model into memory.

        Args:
            model_id: Hugging Face model ID. If None, uses settings.model_id.
        """
        model_id = model_id or settings.model_id

        if model_id in self.model_cache and "txt2img" in self.model_cache[model_id]:
            logger.info(f"Model {model_id} already loaded (txt2img)")
            return

        logger.info(f"Loading txt2img model: {model_id} on device: {self.device}")

        try:
            # Determine dtype based on precision setting
            # MPS requires float32 for the entire pipeline to avoid dtype mismatch errors
            if self.device == "mps":
                torch_dtype = torch.float32
                logger.info("Using float32 for MPS to avoid VAE dtype mismatch")
            else:
                torch_dtype = torch.float16 if settings.model_precision == "fp16" else torch.float32

            # Select the correct pipeline class based on model type
            is_sdxl = self._is_sdxl_model(model_id)
            pipeline_class = StableDiffusionXLPipeline if is_sdxl else StableDiffusionPipeline

            logger.info(f"Using pipeline: {pipeline_class.__name__} (SDXL={is_sdxl}, dtype={torch_dtype})")

            # Load the model
            load_kwargs = {
                "torch_dtype": torch_dtype,
                "token": settings.hf_token,
            }
            # Only add safety_checker for non-SDXL models (SDXL doesn't have it)
            if not is_sdxl:
                load_kwargs["safety_checker"] = None

            pipe = pipeline_class.from_pretrained(model_id, **load_kwargs)

            # Move to device
            if self.device == "cuda":
                pipe = pipe.to("cuda")
            elif self.device == "mps":
                pipe = pipe.to("mps")
            else:
                pipe = pipe.to("cpu")

            # Use faster scheduler (DPM-Solver++)
            pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                pipe.scheduler.config
            )

            # Enable memory optimizations if using GPU
            if self.device in ["cuda", "mps"]:
                pipe.enable_attention_slicing()
                if self.device == "cuda":
                    # Enable xformers memory efficient attention if available
                    try:
                        pipe.enable_xformers_memory_efficient_attention()
                        logger.info("Enabled xformers memory efficient attention")
                    except Exception as e:
                        logger.warning(f"Could not enable xformers: {e}")

            # Cache the loaded model
            if model_id not in self.model_cache:
                self.model_cache[model_id] = {}
            self.model_cache[model_id]["txt2img"] = pipe
            self.current_model_id = model_id

            logger.info(f"Model {model_id} loaded successfully (txt2img)")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def generate_image(
        self,
        prompt: str,
        model_id: str = None,
        negative_prompt: Optional[str] = None,
        num_inference_steps: int = None,
        guidance_scale: float = None,
        width: int = None,
        height: int = None,
        seed: Optional[int] = None,
        progress_callback: Optional[callable] = None,
    ):
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate
            model_id: Hugging Face model ID. If None, uses settings.model_id.
            negative_prompt: What to avoid in the image
            num_inference_steps: Number of denoising steps (quality vs speed)
            guidance_scale: How closely to follow the prompt (7-12 recommended)
            width: Image width in pixels (must be multiple of 8)
            height: Image height in pixels (must be multiple of 8)
            seed: Random seed for reproducibility

        Returns:
            PIL Image object
        """
        model_id = model_id or settings.model_id

        # Load model if not already cached
        if model_id not in self.model_cache or "txt2img" not in self.model_cache[model_id]:
            self.load_model(model_id)

        # Check if SDXL for appropriate defaults
        is_sdxl = self._is_sdxl_model(model_id)

        # Use defaults if not specified (SDXL works best at 1024x1024)
        num_inference_steps = num_inference_steps or settings.default_steps
        guidance_scale = guidance_scale or settings.default_guidance_scale

        if is_sdxl:
            # SDXL native resolution is 1024x1024
            width = width or 1024
            height = height or 1024
        else:
            width = width or settings.default_width
            height = height or settings.default_height

        # Use default negative prompt if none provided
        if not negative_prompt:
            negative_prompt = DEFAULT_NEGATIVE_PROMPT

        logger.info(
            f"Generating image: prompt='{prompt[:50]}...', "
            f"steps={num_inference_steps}, guidance={guidance_scale}, "
            f"size={width}x{height}, seed={seed}"
        )

        try:
            # Set seed for reproducibility
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.device).manual_seed(seed)

            # Get the cached pipeline
            pipe = self.model_cache[model_id]["txt2img"]

            # Create a wrapper callback for diffusers format
            # Note: DPMSolverMultistepScheduler can have off-by-one errors in timestep indexing
            # during callbacks, so we wrap in try-except to handle edge cases gracefully
            def step_callback(pipe_instance, step, timestep, callback_kwargs):
                try:
                    if progress_callback:
                        progress = (step + 1) / num_inference_steps * 100
                        progress_callback(progress)
                except (IndexError, RuntimeError) as e:
                    # Gracefully handle scheduler index overflow (known DPM++ bug)
                    logger.debug(f"Callback step {step} handled: {e}")
                return callback_kwargs

            # Generate image
            result = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                width=width,
                height=height,
                generator=generator,
                callback_on_step_end=step_callback if progress_callback else None,
            )

            image = result.images[0]
            logger.info("Image generated successfully")

            return image

        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            raise

    def load_img2img_model(self, model_id: str = None):
        """Load the img2img pipeline (shares weights with txt2img).

        Args:
            model_id: Hugging Face model ID. If None, uses settings.model_id.
        """
        model_id = model_id or settings.model_id

        if model_id in self.model_cache and "img2img" in self.model_cache[model_id]:
            logger.info(f"Model {model_id} already loaded (img2img)")
            return

        logger.info(f"Loading img2img model: {model_id} on device: {self.device}")

        try:
            # Determine dtype based on precision setting
            # MPS requires float32 for the entire pipeline to avoid dtype mismatch errors
            if self.device == "mps":
                torch_dtype = torch.float32
                logger.info("Using float32 for MPS to avoid VAE dtype mismatch (img2img)")
            else:
                torch_dtype = torch.float16 if settings.model_precision == "fp16" else torch.float32

            # Select the correct pipeline class based on model type
            is_sdxl = self._is_sdxl_model(model_id)
            pipeline_class = StableDiffusionXLImg2ImgPipeline if is_sdxl else StableDiffusionImg2ImgPipeline

            logger.info(f"Using img2img pipeline: {pipeline_class.__name__} (SDXL={is_sdxl}, dtype={torch_dtype})")

            # Load the img2img pipeline
            load_kwargs = {
                "torch_dtype": torch_dtype,
                "token": settings.hf_token,
            }
            # Only add safety_checker for non-SDXL models (SDXL doesn't have it)
            if not is_sdxl:
                load_kwargs["safety_checker"] = None

            img2img_pipe = pipeline_class.from_pretrained(model_id, **load_kwargs)

            # Move to device
            if self.device == "cuda":
                img2img_pipe = img2img_pipe.to("cuda")
            elif self.device == "mps":
                img2img_pipe = img2img_pipe.to("mps")
            else:
                img2img_pipe = img2img_pipe.to("cpu")

            # Use same scheduler as txt2img
            img2img_pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                img2img_pipe.scheduler.config
            )

            # Enable memory optimizations
            if self.device in ["cuda", "mps"]:
                img2img_pipe.enable_attention_slicing()
                if self.device == "cuda":
                    try:
                        img2img_pipe.enable_xformers_memory_efficient_attention()
                    except Exception as e:
                        logger.warning(f"Could not enable xformers for img2img: {e}")

            # Cache the loaded model
            if model_id not in self.model_cache:
                self.model_cache[model_id] = {}
            self.model_cache[model_id]["img2img"] = img2img_pipe
            self.current_model_id = model_id

            logger.info(f"Model {model_id} loaded successfully (img2img)")

        except Exception as e:
            logger.error(f"Failed to load img2img pipeline: {e}")
            raise

    def generate_image_from_image(
        self,
        init_image: Image.Image,
        prompt: str,
        model_id: str = None,
        strength: float = 0.75,
        negative_prompt: Optional[str] = None,
        num_inference_steps: int = None,
        guidance_scale: float = None,
        seed: Optional[int] = None,
        progress_callback: Optional[callable] = None,
    ):
        """
        Generate an image from an initial image and prompt (img2img).

        Args:
            init_image: PIL Image to use as starting point
            prompt: Text description of desired transformation
            model_id: Hugging Face model ID. If None, uses settings.model_id.
            strength: How much to transform (0.0=keep original, 1.0=complete transform)
            negative_prompt: What to avoid in the image
            num_inference_steps: Number of denoising steps
            guidance_scale: How closely to follow the prompt
            seed: Random seed for reproducibility

        Returns:
            PIL Image object
        """
        model_id = model_id or settings.model_id

        # Load model if not already cached
        if model_id not in self.model_cache or "img2img" not in self.model_cache[model_id]:
            self.load_img2img_model(model_id)

        # Use defaults if not specified
        num_inference_steps = num_inference_steps or settings.default_steps
        guidance_scale = guidance_scale or settings.default_guidance_scale

        # Use default negative prompt if none provided
        if not negative_prompt:
            negative_prompt = DEFAULT_NEGATIVE_PROMPT

        logger.info(
            f"Generating img2img: prompt='{prompt[:50]}...', "
            f"strength={strength}, steps={num_inference_steps}, "
            f"guidance={guidance_scale}, seed={seed}"
        )

        try:
            # Preprocess init image (resize if needed)
            # Stable Diffusion works best with dimensions that are multiples of 8
            width, height = init_image.size

            # Resize if too large
            max_size = 1024
            if width > max_size or height > max_size:
                if width > height:
                    new_width = max_size
                    new_height = int((max_size / width) * height)
                else:
                    new_height = max_size
                    new_width = int((max_size / height) * width)

                # Make sure dimensions are multiples of 8
                new_width = (new_width // 8) * 8
                new_height = (new_height // 8) * 8

                init_image = init_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"Resized init image from {width}x{height} to {new_width}x{new_height}")

            # Convert to RGB if needed
            if init_image.mode != "RGB":
                init_image = init_image.convert("RGB")

            # Set seed for reproducibility
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.device).manual_seed(seed)

            # Get the cached pipeline
            img2img_pipe = self.model_cache[model_id]["img2img"]

            # Create a wrapper callback for diffusers format
            # Note: DPMSolverMultistepScheduler can have off-by-one errors in timestep indexing
            # during callbacks, so we wrap in try-except to handle edge cases gracefully
            def step_callback(pipe_instance, step, timestep, callback_kwargs):
                try:
                    if progress_callback:
                        progress = (step + 1) / num_inference_steps * 100
                        progress_callback(progress)
                except (IndexError, RuntimeError) as e:
                    # Gracefully handle scheduler index overflow (known DPM++ bug)
                    logger.debug(f"Callback step {step} handled: {e}")
                return callback_kwargs

            # Generate image
            result = img2img_pipe(
                prompt=prompt,
                image=init_image,
                strength=strength,
                negative_prompt=negative_prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
                callback_on_step_end=step_callback if progress_callback else None,
            )

            image = result.images[0]
            logger.info("Img2img generation successful")

            return image

        except Exception as e:
            logger.error(f"Failed to generate img2img: {e}")
            raise

    def unload_model(self, model_id: str = None):
        """Unload models from memory to free resources.

        Args:
            model_id: Specific model ID to unload. If None, unloads all cached models.
        """
        if model_id:
            # Unload specific model
            if model_id in self.model_cache:
                logger.info(f"Unloading model: {model_id}")
                del self.model_cache[model_id]
                logger.info(f"Model {model_id} unloaded")
            else:
                logger.warning(f"Model {model_id} not found in cache")
        else:
            # Unload all models
            if self.model_cache:
                logger.info(f"Unloading all models ({len(self.model_cache)} cached)")
                self.model_cache.clear()
                logger.info("All models unloaded")

        # Clear CUDA cache if using GPU
        if self.device == "cuda":
            torch.cuda.empty_cache()

    @property
    def is_loaded(self) -> bool:
        """Check if any model is currently loaded."""
        return len(self.model_cache) > 0


# Global model instance
sd_model = StableDiffusionModel()
