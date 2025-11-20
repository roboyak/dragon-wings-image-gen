"""Stable Diffusion model management."""
import os
import logging
from typing import Optional
import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from .config import settings

logger = logging.getLogger(__name__)


class StableDiffusionModel:
    """Manages the Stable Diffusion model lifecycle."""

    def __init__(self):
        self.pipe: Optional[StableDiffusionPipeline] = None
        self.device = settings.device
        self.model_id = settings.model_id
        self.is_loaded = False

    def load_model(self):
        """Load the Stable Diffusion model into memory."""
        if self.is_loaded:
            logger.info("Model already loaded")
            return

        logger.info(f"Loading model: {self.model_id} on device: {self.device}")

        try:
            # Determine dtype based on precision setting
            torch_dtype = torch.float16 if settings.model_precision == "fp16" else torch.float32

            # Load the model
            self.pipe = StableDiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch_dtype,
                use_auth_token=settings.hf_token,
                safety_checker=None,  # Disable for POC (enable in production)
            )

            # Move to device
            if self.device == "cuda":
                self.pipe = self.pipe.to("cuda")
            elif self.device == "mps":
                self.pipe = self.pipe.to("mps")
            else:
                self.pipe = self.pipe.to("cpu")

            # Use faster scheduler (DPM-Solver++)
            self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipe.scheduler.config
            )

            # Enable memory optimizations if using GPU
            if self.device in ["cuda", "mps"]:
                self.pipe.enable_attention_slicing()
                if self.device == "cuda":
                    # Enable xformers memory efficient attention if available
                    try:
                        self.pipe.enable_xformers_memory_efficient_attention()
                        logger.info("Enabled xformers memory efficient attention")
                    except Exception as e:
                        logger.warning(f"Could not enable xformers: {e}")

            self.is_loaded = True
            logger.info("Model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        num_inference_steps: int = None,
        guidance_scale: float = None,
        width: int = None,
        height: int = None,
        seed: Optional[int] = None,
    ):
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate
            negative_prompt: What to avoid in the image
            num_inference_steps: Number of denoising steps (quality vs speed)
            guidance_scale: How closely to follow the prompt (7-12 recommended)
            width: Image width in pixels (must be multiple of 8)
            height: Image height in pixels (must be multiple of 8)
            seed: Random seed for reproducibility

        Returns:
            PIL Image object
        """
        if not self.is_loaded:
            self.load_model()

        # Use defaults if not specified
        num_inference_steps = num_inference_steps or settings.default_steps
        guidance_scale = guidance_scale or settings.default_guidance_scale
        width = width or settings.default_width
        height = height or settings.default_height

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

            # Generate image
            result = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                width=width,
                height=height,
                generator=generator,
            )

            image = result.images[0]
            logger.info("Image generated successfully")

            return image

        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            raise

    def unload_model(self):
        """Unload model from memory to free resources."""
        if self.is_loaded:
            logger.info("Unloading model...")
            del self.pipe
            self.pipe = None
            self.is_loaded = False

            # Clear CUDA cache if using GPU
            if self.device == "cuda":
                torch.cuda.empty_cache()

            logger.info("Model unloaded")


# Global model instance
sd_model = StableDiffusionModel()
