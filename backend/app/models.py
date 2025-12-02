"""Stable Diffusion model management."""
import os
import logging
from typing import Optional, List, Dict, Any
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
    StableDiffusionInpaintPipeline,
    StableDiffusionXLPipeline,
    StableDiffusionXLImg2ImgPipeline,
    StableDiffusionXLInpaintPipeline,
    DPMSolverMultistepScheduler,
    FluxPipeline,
)
from PIL import ImageFilter
from .config import settings, LORA_CONFIGS, INPAINT_DEFAULTS

logger = logging.getLogger(__name__)


class StableDiffusionModel:
    """Manages the Stable Diffusion model lifecycle with multi-model support."""

    # SDXL model identifiers
    SDXL_MODEL_IDS = [
        "stabilityai/stable-diffusion-xl-base-1.0",
        "stabilityai/stable-diffusion-xl-refiner-1.0",
    ]

    # FLUX model identifiers
    FLUX_MODEL_IDS = [
        "black-forest-labs/FLUX.1-schnell",
        "black-forest-labs/FLUX.1-dev",
    ]

    def __init__(self):
        # Cache for loaded models: {model_id: {"txt2img": pipe, "img2img": pipe}}
        self.model_cache = {}
        self.device = settings.device
        self.current_model_id = settings.model_id
        # Track loaded LoRAs: {model_id: {lora_key: adapter_name}}
        self.loaded_loras: Dict[str, Dict[str, str]] = {}

    def _is_sdxl_model(self, model_id: str) -> bool:
        """Check if the model is an SDXL model."""
        return any(sdxl_id in model_id for sdxl_id in self.SDXL_MODEL_IDS)

    def _is_flux_model(self, model_id: str) -> bool:
        """Check if the model is a FLUX model."""
        return any(flux_id in model_id for flux_id in self.FLUX_MODEL_IDS)

    def _get_model_key_from_id(self, model_id: str) -> Optional[str]:
        """Get the model key from a model ID by searching MODEL_CONFIGS."""
        from .config import MODEL_CONFIGS
        for key, config in MODEL_CONFIGS.items():
            if config["model_id"] == model_id:
                return key
        return None

    def load_lora(
        self,
        pipeline,
        lora_key: str,
        model_key: str,
        weight: float = None,
    ) -> Optional[str]:
        """Load a LoRA adapter onto a pipeline.

        Args:
            pipeline: The diffusers pipeline to load the LoRA onto
            lora_key: The LoRA identifier (e.g., 'thangka', 'watercolor')
            model_key: The model key (e.g., 'sd-v1-5', 'sdxl') for compatibility check
            weight: Optional weight override (uses default from config if not specified)

        Returns:
            The adapter name if successfully loaded, None otherwise
        """
        # Get LoRA config
        if lora_key not in LORA_CONFIGS:
            logger.warning(f"Unknown LoRA key: {lora_key}")
            return None

        lora_config = LORA_CONFIGS[lora_key]

        # Check for local path first, then fall back to HuggingFace ID
        local_path = lora_config.get("local_path")
        lora_id = lora_config.get("lora_id")

        # Determine which source to use
        if local_path and os.path.exists(local_path):
            lora_source = local_path
            source_type = "local"
            logger.info(f"Using local LoRA file: {local_path}")
        elif lora_id and "TODO:" not in lora_id:
            lora_source = lora_id
            source_type = "huggingface"
        else:
            logger.warning(f"LoRA '{lora_key}' has no valid source. "
                          f"local_path={local_path}, lora_id={lora_id}")
            return None

        # Check compatibility
        if not settings.is_lora_compatible(lora_key, model_key):
            logger.warning(
                f"LoRA '{lora_key}' is not compatible with model '{model_key}'. "
                f"Compatible models: {lora_config.get('compatible_models', [])}"
            )
            return None

        # Get model_id from the pipeline for tracking
        model_id = getattr(pipeline.config, '_name_or_path', None) or str(id(pipeline))

        # Check if already loaded
        if model_id in self.loaded_loras and lora_key in self.loaded_loras[model_id]:
            adapter_name = self.loaded_loras[model_id][lora_key]
            logger.info(f"LoRA '{lora_key}' already loaded as '{adapter_name}'")
            return adapter_name

        # Load the LoRA
        adapter_name = lora_key  # Use lora_key as adapter name
        try:
            logger.info(f"Loading LoRA '{lora_key}' from {source_type}: '{lora_source}'")
            pipeline.load_lora_weights(lora_source, adapter_name=adapter_name)

            # Track the loaded LoRA
            if model_id not in self.loaded_loras:
                self.loaded_loras[model_id] = {}
            self.loaded_loras[model_id][lora_key] = adapter_name

            logger.info(f"LoRA '{lora_key}' loaded successfully as adapter '{adapter_name}'")
            return adapter_name

        except Exception as e:
            logger.error(f"Failed to load LoRA '{lora_key}' from {source_type}: {e}")
            return None

    def apply_loras(
        self,
        pipeline,
        lora_specs: List[Dict[str, Any]],
        model_key: str,
    ) -> List[str]:
        """Apply multiple LoRAs to a pipeline with specified weights.

        Args:
            pipeline: The diffusers pipeline to apply LoRAs to
            lora_specs: List of dicts with 'key' and optional 'weight' keys
                       e.g., [{"key": "thangka", "weight": 0.8}, {"key": "watercolor"}]
            model_key: The model key for compatibility checks

        Returns:
            List of trigger words to prepend to prompt (if any)
        """
        if not lora_specs:
            # No LoRAs requested - disable any active ones
            try:
                pipeline.disable_lora()
                logger.info("Disabled LoRA (no LoRAs requested)")
            except Exception as e:
                logger.debug(f"disable_lora not needed or failed: {e}")
            return []

        # Load each LoRA and collect adapter names/weights
        adapter_names = []
        adapter_weights = []
        trigger_words = []

        for spec in lora_specs:
            lora_key = spec.get("key")
            if not lora_key:
                continue

            # Get LoRA config for default weight and trigger words
            lora_config = LORA_CONFIGS.get(lora_key, {})
            default_weight = lora_config.get("default_weight", 0.8)
            weight = spec.get("weight", default_weight)

            # Load the LoRA if not already loaded
            adapter_name = self.load_lora(pipeline, lora_key, model_key, weight)
            if adapter_name:
                adapter_names.append(adapter_name)
                adapter_weights.append(weight)
                # Collect trigger words
                lora_triggers = lora_config.get("trigger_words", [])
                if lora_triggers:
                    trigger_words.extend(lora_triggers[:1])  # Take first trigger word

        # Apply the loaded LoRAs
        if adapter_names:
            try:
                pipeline.set_adapters(adapter_names, adapter_weights=adapter_weights)
                logger.info(
                    f"Applied {len(adapter_names)} LoRA(s): "
                    f"{list(zip(adapter_names, adapter_weights))}"
                )
            except Exception as e:
                logger.error(f"Failed to set adapters: {e}")
        else:
            # No LoRAs were successfully loaded - disable any active ones
            try:
                pipeline.disable_lora()
                logger.info("No LoRAs loaded successfully, disabled LoRA")
            except Exception as e:
                logger.debug(f"disable_lora not needed or failed: {e}")

        return trigger_words

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
            # Detect model type
            is_flux = self._is_flux_model(model_id)
            is_sdxl = self._is_sdxl_model(model_id)

            # Determine dtype based on precision setting and model type
            # MPS requires float32 for SD pipelines to avoid dtype mismatch errors
            # FLUX can use bfloat16 on MPS for better performance
            if is_flux:
                # FLUX works well with bfloat16
                torch_dtype = torch.bfloat16
                logger.info("Using bfloat16 for FLUX model")
            elif self.device == "mps":
                torch_dtype = torch.float32
                logger.info("Using float32 for MPS to avoid VAE dtype mismatch")
            else:
                torch_dtype = torch.float16 if settings.model_precision == "fp16" else torch.float32

            # Select the correct pipeline class based on model type
            if is_flux:
                pipeline_class = FluxPipeline
            elif is_sdxl:
                pipeline_class = StableDiffusionXLPipeline
            else:
                pipeline_class = StableDiffusionPipeline

            logger.info(f"Using pipeline: {pipeline_class.__name__} (FLUX={is_flux}, SDXL={is_sdxl}, dtype={torch_dtype})")

            # Load the model
            load_kwargs = {
                "torch_dtype": torch_dtype,
                "token": settings.hf_token,
            }
            # Only add safety_checker for non-SDXL and non-FLUX models
            if not is_sdxl and not is_flux:
                load_kwargs["safety_checker"] = None

            pipe = pipeline_class.from_pretrained(model_id, **load_kwargs)

            # Move to device
            if self.device == "cuda":
                pipe = pipe.to("cuda")
            elif self.device == "mps":
                pipe = pipe.to("mps")
            else:
                pipe = pipe.to("cpu")

            # Configure scheduler (only for SD models, FLUX uses its own)
            if not is_flux:
                # Use faster scheduler (DPM-Solver++)
                # Some models (like Realistic Vision) have scheduler configs with incompatible
                # combinations (e.g., final_sigmas_type=zero with algorithm_type=deis).
                # We override these to ensure compatibility.
                scheduler_config = dict(pipe.scheduler.config)
                # Remove problematic config options that cause compatibility issues
                scheduler_config.pop("final_sigmas_type", None)
                scheduler_config.pop("algorithm_type", None)
                pipe.scheduler = DPMSolverMultistepScheduler.from_config(scheduler_config)

            # Enable memory optimizations if using GPU
            if self.device in ["cuda", "mps"]:
                if not is_flux:
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
        lora_specs: Optional[List[Dict[str, Any]]] = None,
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
            progress_callback: Callback function for progress updates
            lora_specs: Optional list of LoRA specifications, each with 'key' and optional 'weight'
                       e.g., [{"key": "thangka", "weight": 0.8}]

        Returns:
            PIL Image object
        """
        model_id = model_id or settings.model_id

        # Load model if not already cached
        if model_id not in self.model_cache or "txt2img" not in self.model_cache[model_id]:
            self.load_model(model_id)

        # Check model type for appropriate defaults
        is_flux = self._is_flux_model(model_id)
        is_sdxl = self._is_sdxl_model(model_id)

        # Set defaults based on model type
        if is_flux:
            # FLUX schnell uses 4 steps and no guidance
            num_inference_steps = num_inference_steps or 4
            guidance_scale = guidance_scale if guidance_scale is not None else 0.0
            width = width or 1024
            height = height or 1024
            # FLUX doesn't use negative prompts
            negative_prompt = None
            # FLUX doesn't support LoRAs in the same way
            if lora_specs:
                logger.warning("LoRAs are not supported with FLUX models. Ignoring lora_specs.")
                lora_specs = None
        elif is_sdxl:
            # SDXL native resolution is 1024x1024
            num_inference_steps = num_inference_steps or settings.default_steps
            guidance_scale = guidance_scale or settings.default_guidance_scale
            width = width or 1024
            height = height or 1024
            if not negative_prompt:
                negative_prompt = DEFAULT_NEGATIVE_PROMPT
        else:
            num_inference_steps = num_inference_steps or settings.default_steps
            guidance_scale = guidance_scale or settings.default_guidance_scale
            width = width or settings.default_width
            height = height or settings.default_height
            if not negative_prompt:
                negative_prompt = DEFAULT_NEGATIVE_PROMPT

        logger.info(
            f"Generating image: prompt='{prompt[:50]}...', "
            f"steps={num_inference_steps}, guidance={guidance_scale}, "
            f"size={width}x{height}, seed={seed}, loras={lora_specs}"
        )

        try:
            # Set seed for reproducibility
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.device).manual_seed(seed)

            # Get the cached pipeline
            pipe = self.model_cache[model_id]["txt2img"]

            # Apply LoRAs if specified (not supported for FLUX)
            trigger_words = []
            if lora_specs and not is_flux:
                # Determine model_key for compatibility check
                model_key = self._get_model_key_from_id(model_id)
                if model_key:
                    trigger_words = self.apply_loras(pipe, lora_specs, model_key)
                else:
                    logger.warning(f"Could not determine model_key for {model_id}, skipping LoRA application")

            # Prepend trigger words to prompt if any
            if trigger_words:
                trigger_prefix = ", ".join(trigger_words) + ", "
                prompt = trigger_prefix + prompt
                logger.info(f"Prepended trigger words to prompt: {trigger_prefix}")

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

            # Generate image - FLUX uses different parameters
            if is_flux:
                result = pipe(
                    prompt=prompt,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    width=width,
                    height=height,
                    generator=generator,
                    # FLUX doesn't support callback_on_step_end in the same way
                )
            else:
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
            # Remove problematic config options for compatibility (same as txt2img)
            scheduler_config = dict(img2img_pipe.scheduler.config)
            scheduler_config.pop("final_sigmas_type", None)
            scheduler_config.pop("algorithm_type", None)
            img2img_pipe.scheduler = DPMSolverMultistepScheduler.from_config(scheduler_config)

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

    def load_inpaint_model(self, model_id: str = None):
        """Load the inpainting pipeline for a model.

        Uses dedicated inpainting models (runwayml/stable-diffusion-inpainting for SD 1.5,
        diffusers/stable-diffusion-xl-1.0-inpainting-0.1 for SDXL) for better quality.

        Args:
            model_id: Hugging Face model ID of the BASE model. The corresponding
                     inpainting model will be loaded automatically.
        """
        model_id = model_id or settings.model_id

        if model_id in self.model_cache and "inpaint" in self.model_cache[model_id]:
            logger.info(f"Model {model_id} already loaded (inpaint)")
            return

        # Get model key to find the right inpainting model
        model_key = self._get_model_key_from_id(model_id)
        if not model_key:
            raise ValueError(f"Unknown model ID: {model_id}")

        # Check if inpainting is supported
        if not settings.supports_inpaint(model_key):
            raise ValueError(f"Model '{model_key}' does not support inpainting")

        # Get the dedicated inpainting model ID
        inpaint_model_id = settings.get_inpaint_model_id(model_key)
        if not inpaint_model_id:
            raise ValueError(f"No inpainting model found for '{model_key}'")

        logger.info(f"Loading inpaint model: {inpaint_model_id} for base model: {model_id}")

        try:
            # Determine dtype based on device
            is_sdxl = self._is_sdxl_model(model_id)
            if self.device == "mps":
                torch_dtype = torch.float32
                logger.info("Using float32 for MPS to avoid VAE dtype mismatch (inpaint)")
            else:
                torch_dtype = torch.float16 if settings.model_precision == "fp16" else torch.float32

            # Select the correct inpainting pipeline class
            pipeline_class = StableDiffusionXLInpaintPipeline if is_sdxl else StableDiffusionInpaintPipeline

            logger.info(f"Using inpaint pipeline: {pipeline_class.__name__} (SDXL={is_sdxl}, dtype={torch_dtype})")

            # Load the inpainting pipeline
            load_kwargs = {
                "torch_dtype": torch_dtype,
                "token": settings.hf_token,
            }
            # Only add safety_checker for non-SDXL models
            if not is_sdxl:
                load_kwargs["safety_checker"] = None

            inpaint_pipe = pipeline_class.from_pretrained(inpaint_model_id, **load_kwargs)

            # Move to device
            if self.device == "cuda":
                inpaint_pipe = inpaint_pipe.to("cuda")
            elif self.device == "mps":
                inpaint_pipe = inpaint_pipe.to("mps")
            else:
                inpaint_pipe = inpaint_pipe.to("cpu")

            # Use DPM-Solver++ scheduler for faster inference
            scheduler_config = dict(inpaint_pipe.scheduler.config)
            scheduler_config.pop("final_sigmas_type", None)
            scheduler_config.pop("algorithm_type", None)
            inpaint_pipe.scheduler = DPMSolverMultistepScheduler.from_config(scheduler_config)

            # Enable memory optimizations
            if self.device in ["cuda", "mps"]:
                inpaint_pipe.enable_attention_slicing()
                if self.device == "cuda":
                    try:
                        inpaint_pipe.enable_xformers_memory_efficient_attention()
                    except Exception as e:
                        logger.warning(f"Could not enable xformers for inpaint: {e}")

            # Cache under the BASE model ID so we can look it up consistently
            if model_id not in self.model_cache:
                self.model_cache[model_id] = {}
            self.model_cache[model_id]["inpaint"] = inpaint_pipe
            self.current_model_id = model_id

            logger.info(f"Inpaint model loaded successfully for {model_id}")

        except Exception as e:
            logger.error(f"Failed to load inpaint pipeline: {e}")
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
        lora_specs: Optional[List[Dict[str, Any]]] = None,
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
            progress_callback: Callback function for progress updates
            lora_specs: Optional list of LoRA specifications, each with 'key' and optional 'weight'
                       e.g., [{"key": "thangka", "weight": 0.8}]

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
            f"guidance={guidance_scale}, seed={seed}, loras={lora_specs}"
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

            # Apply LoRAs if specified
            trigger_words = []
            if lora_specs:
                # Determine model_key for compatibility check
                model_key = self._get_model_key_from_id(model_id)
                if model_key:
                    trigger_words = self.apply_loras(img2img_pipe, lora_specs, model_key)
                else:
                    logger.warning(f"Could not determine model_key for {model_id}, skipping LoRA application")

            # Prepend trigger words to prompt if any
            if trigger_words:
                trigger_prefix = ", ".join(trigger_words) + ", "
                prompt = trigger_prefix + prompt
                logger.info(f"Prepended trigger words to prompt: {trigger_prefix}")

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

    def preprocess_mask(
        self,
        mask: Image.Image,
        target_size: tuple,
        blur_mask: bool = True,
        blur_factor: int = None,
    ) -> Image.Image:
        """Preprocess mask image for inpainting.

        Args:
            mask: PIL Image mask (white=inpaint, black=preserve)
            target_size: (width, height) tuple to resize mask to
            blur_mask: Whether to apply Gaussian blur for smoother edges
            blur_factor: Blur radius (uses INPAINT_DEFAULTS if not specified)

        Returns:
            Preprocessed PIL Image in grayscale mode
        """
        # Convert to grayscale if needed
        if mask.mode != "L":
            mask = mask.convert("L")

        # Resize to match target dimensions
        if mask.size != target_size:
            mask = mask.resize(target_size, Image.Resampling.LANCZOS)
            logger.info(f"Resized mask from {mask.size} to {target_size}")

        # Ensure dimensions are multiples of 8
        w, h = mask.size
        new_w = (w // 8) * 8
        new_h = (h // 8) * 8
        if (new_w, new_h) != (w, h):
            mask = mask.resize((new_w, new_h), Image.Resampling.LANCZOS)
            logger.info(f"Adjusted mask to multiples of 8: {new_w}x{new_h}")

        # Apply Gaussian blur for smoother edges
        if blur_mask:
            blur_factor = blur_factor or INPAINT_DEFAULTS["blur_factor"]
            mask = mask.filter(ImageFilter.GaussianBlur(radius=blur_factor))
            logger.info(f"Applied Gaussian blur with radius {blur_factor}")

        return mask

    def generate_image_inpaint(
        self,
        init_image: Image.Image,
        mask_image: Image.Image,
        prompt: str,
        model_id: str = None,
        strength: float = None,
        negative_prompt: Optional[str] = None,
        num_inference_steps: int = None,
        guidance_scale: float = None,
        seed: Optional[int] = None,
        blur_mask: bool = None,
        blur_factor: int = None,
        progress_callback: Optional[callable] = None,
        lora_specs: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Generate an image using inpainting (selective region editing).

        Args:
            init_image: PIL Image to use as base
            mask_image: PIL Image mask (white=inpaint, black=preserve)
            prompt: Text description of what to paint in masked region
            model_id: Hugging Face model ID. If None, uses settings.model_id.
            strength: How much to transform masked region (0.0-1.0)
            negative_prompt: What to avoid in the image
            num_inference_steps: Number of denoising steps
            guidance_scale: How closely to follow the prompt
            seed: Random seed for reproducibility
            blur_mask: Whether to blur mask edges for smoother blending
            blur_factor: Gaussian blur radius for mask
            progress_callback: Callback function for progress updates
            lora_specs: Optional list of LoRA specifications

        Returns:
            PIL Image object with inpainted result
        """
        model_id = model_id or settings.model_id

        # Load inpainting model if not already cached
        if model_id not in self.model_cache or "inpaint" not in self.model_cache[model_id]:
            self.load_inpaint_model(model_id)

        # Use defaults from config
        strength = strength if strength is not None else INPAINT_DEFAULTS["strength"]
        blur_mask = blur_mask if blur_mask is not None else INPAINT_DEFAULTS["blur_mask"]
        blur_factor = blur_factor if blur_factor is not None else INPAINT_DEFAULTS["blur_factor"]
        num_inference_steps = num_inference_steps or settings.default_steps
        guidance_scale = guidance_scale or settings.default_guidance_scale

        # Use default negative prompt if none provided
        if not negative_prompt:
            negative_prompt = DEFAULT_NEGATIVE_PROMPT

        logger.info(
            f"Generating inpaint: prompt='{prompt[:50]}...', "
            f"strength={strength}, steps={num_inference_steps}, "
            f"guidance={guidance_scale}, seed={seed}, blur={blur_mask}, loras={lora_specs}"
        )

        try:
            # Preprocess init image
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
                width, height = new_width, new_height

            # Ensure dimensions are multiples of 8
            new_width = (width // 8) * 8
            new_height = (height // 8) * 8
            if (new_width, new_height) != (width, height):
                init_image = init_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"Adjusted init image to multiples of 8: {new_width}x{new_height}")
                width, height = new_width, new_height

            # Convert to RGB if needed
            if init_image.mode != "RGB":
                init_image = init_image.convert("RGB")

            # Preprocess mask to match init image
            processed_mask = self.preprocess_mask(
                mask_image,
                target_size=(width, height),
                blur_mask=blur_mask,
                blur_factor=blur_factor,
            )

            # Set seed for reproducibility
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.device).manual_seed(seed)

            # Get the cached inpainting pipeline
            inpaint_pipe = self.model_cache[model_id]["inpaint"]

            # Apply LoRAs if specified
            trigger_words = []
            if lora_specs:
                model_key = self._get_model_key_from_id(model_id)
                if model_key:
                    trigger_words = self.apply_loras(inpaint_pipe, lora_specs, model_key)
                else:
                    logger.warning(f"Could not determine model_key for {model_id}, skipping LoRA application")

            # Prepend trigger words to prompt if any
            if trigger_words:
                trigger_prefix = ", ".join(trigger_words) + ", "
                prompt = trigger_prefix + prompt
                logger.info(f"Prepended trigger words to prompt: {trigger_prefix}")

            # Create progress callback
            def step_callback(pipe_instance, step, timestep, callback_kwargs):
                try:
                    if progress_callback:
                        progress = (step + 1) / num_inference_steps * 100
                        progress_callback(progress)
                except (IndexError, RuntimeError) as e:
                    logger.debug(f"Callback step {step} handled: {e}")
                return callback_kwargs

            # Generate inpainted image
            result = inpaint_pipe(
                prompt=prompt,
                image=init_image,
                mask_image=processed_mask,
                negative_prompt=negative_prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                strength=strength,
                generator=generator,
                callback_on_step_end=step_callback if progress_callback else None,
            )

            image = result.images[0]
            logger.info("Inpaint generation successful")

            return image

        except Exception as e:
            logger.error(f"Failed to generate inpaint: {e}")
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
                # Also clear LoRA tracking for this model
                if model_id in self.loaded_loras:
                    del self.loaded_loras[model_id]
                logger.info(f"Model {model_id} unloaded")
            else:
                logger.warning(f"Model {model_id} not found in cache")
        else:
            # Unload all models
            if self.model_cache:
                logger.info(f"Unloading all models ({len(self.model_cache)} cached)")
                self.model_cache.clear()
                self.loaded_loras.clear()  # Clear all LoRA tracking
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
