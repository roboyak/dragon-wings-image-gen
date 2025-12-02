"""Configuration management for the backend."""
from pydantic_settings import BaseSettings
from typing import List, Dict, Any


# Available Stable Diffusion models
MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "sd-v1-5": {
        "model_id": "runwayml/stable-diffusion-v1-5",
        "name": "Stable Diffusion v1.5",
        "description": "Fast, lightweight, general-purpose model",
        "native_resolution": 512,
        "recommended_for": "General use, fast generation, limited hardware",
        "strengths": ["Speed", "Low memory usage", "General objects"],
        "weaknesses": ["Limited artistic styles", "Lower quality details"],
        "ram_required_gb": 4,
        "txt2img": True,
        "img2img": True,
        "inpaint": True,
    },
    "openjourney": {
        "model_id": "prompthero/openjourney",
        "name": "OpenJourney",
        "description": "Midjourney-style artistic images",
        "native_resolution": 512,
        "recommended_for": "Artistic, stylized images with Midjourney aesthetic",
        "strengths": ["Artistic style", "Beautiful renders", "No license required"],
        "weaknesses": ["Less photorealistic", "Specific style"],
        "ram_required_gb": 4,
        "txt2img": True,
        "img2img": True,
        "inpaint": True,
    },
    "sdxl": {
        "model_id": "stabilityai/stable-diffusion-xl-base-1.0",
        "name": "Stable Diffusion XL",
        "description": "Highest quality, excellent artistic style transfer (GPU required)",
        "native_resolution": 1024,
        "recommended_for": "Professional quality, artistic transformations, style transfer",
        "strengths": ["Exceptional quality", "Artistic styles", "1024x1024 resolution", "Detail preservation"],
        "weaknesses": ["Slow generation", "High memory usage", "Requires GPU"],
        "ram_required_gb": 12,
        "txt2img": True,
        "img2img": True,
        "inpaint": True,
        "requires_gpu": True,
    },
    "realistic-vision": {
        "model_id": "SG161222/Realistic_Vision_V5.1_noVAE",
        "name": "Realistic Vision v5.1",
        "description": "Photorealistic portraits and scenes",
        "native_resolution": 512,
        "recommended_for": "Photorealistic images, portraits, natural scenes",
        "strengths": ["Photorealism", "Portraits", "Skin textures", "Natural lighting"],
        "weaknesses": ["Less artistic/stylized", "Can look too perfect"],
        "ram_required_gb": 4,
        "txt2img": True,
        "img2img": True,
        "inpaint": True,
    },
    "dreamshaper": {
        "model_id": "Lykon/dreamshaper-8",
        "name": "DreamShaper 8",
        "description": "Fantasy and artistic illustrations",
        "native_resolution": 512,
        "recommended_for": "Fantasy art, illustrations, stylized portraits",
        "strengths": ["Artistic style", "Fantasy themes", "Beautiful colors", "Detailed backgrounds"],
        "weaknesses": ["Less photorealistic", "Specific artistic style"],
        "ram_required_gb": 4,
        "txt2img": True,
        "img2img": True,
        "inpaint": True,
    },
    "analog-diffusion": {
        "model_id": "wavymulder/Analog-Diffusion",
        "name": "Analog Diffusion",
        "description": "Vintage film photography aesthetic",
        "native_resolution": 512,
        "recommended_for": "Film photography look, vintage aesthetic, nostalgic images",
        "strengths": ["Film grain", "Vintage colors", "Nostalgic mood", "Natural imperfections"],
        "weaknesses": ["Specific style only", "Add 'analog style' to prompt"],
        "ram_required_gb": 4,
        "txt2img": True,
        "img2img": True,
        "inpaint": True,
        "prompt_suffix": "analog style",
    },
    "flux-schnell": {
        "model_id": "black-forest-labs/FLUX.1-schnell",
        "name": "FLUX.1 Schnell",
        "description": "State-of-art quality, excellent text rendering, fast generation",
        "native_resolution": 1024,
        "recommended_for": "High quality images, text in images, professional results",
        "strengths": ["Best quality", "Text rendering", "Prompt following", "Fast for its quality"],
        "weaknesses": ["Large model (~12GB)", "Higher memory usage", "No inpainting support"],
        "ram_required_gb": 12,
        "txt2img": True,
        "img2img": False,
        "inpaint": False,
        "pipeline_type": "flux",
    },
}

# SD 1.5-based models that share LoRA compatibility
SD15_COMPATIBLE_MODELS = ["sd-v1-5", "openjourney", "realistic-vision", "dreamshaper", "analog-diffusion"]
SDXL_COMPATIBLE_MODELS = ["sdxl"]

# Dedicated inpainting models (better quality than using base models)
INPAINT_MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "sd15": {
        "model_id": "runwayml/stable-diffusion-inpainting",
        "name": "SD 1.5 Inpainting",
        "description": "Dedicated inpainting model for SD 1.5 base models",
        "native_resolution": 512,
        "compatible_base_models": SD15_COMPATIBLE_MODELS,
    },
    "sdxl": {
        "model_id": "diffusers/stable-diffusion-xl-1.0-inpainting-0.1",
        "name": "SDXL Inpainting",
        "description": "Dedicated inpainting model for SDXL",
        "native_resolution": 1024,
        "compatible_base_models": SDXL_COMPATIBLE_MODELS,
    },
}

# Default mask preprocessing settings
INPAINT_DEFAULTS = {
    "blur_mask": True,
    "blur_factor": 33,  # Higher = softer edges
    "strength": 0.8,    # How much to change masked area (0.0-1.0)
}

# Local LoRA storage directory (relative to backend root)
LORA_LOCAL_DIR = "./loras"

# Available LoRA adapters for style customization
# Each LoRA can have either:
#   - lora_id: HuggingFace repo ID (auto-downloads and caches)
#   - local_path: Path to local .safetensors file (takes precedence if present)
LORA_CONFIGS: Dict[str, Dict[str, Any]] = {
    "watercolor": {
        "lora_id": "SydigiAI/WaterColorStyle-loRA",  # HuggingFace fallback
        "local_path": "./loras/watercolor.safetensors",  # Local file (preferred)
        "name": "Watercolor Painting",
        "description": "Soft, flowing watercolor aesthetic with transparent washes and organic edges",
        "default_weight": 0.7,
        "weight_range": {"min": 0.0, "max": 1.2},
        "compatible_models": SD15_COMPATIBLE_MODELS,
        "trigger_words": ["Sora WaterColor", "watercolor", "watercolor painting"],
        "category": "artistic",
    },
    "anime-ghibli": {
        "lora_id": "artificialguybr/studioghibli-redmond-1-5v-studio-ghibli-lora-for-liberteredmond-sd-1-5",
        "local_path": "./loras/anime-ghibli.safetensors",  # Local file (preferred)
        "name": "Studio Ghibli Style",
        "description": "Studio Ghibli and anime aesthetic with soft colors, detailed backgrounds, and whimsical feel",
        "default_weight": 0.75,
        "weight_range": {"min": 0.0, "max": 1.2},
        "compatible_models": SD15_COMPATIBLE_MODELS,
        "trigger_words": ["Studio Ghibli", "StdGBRedmAF", "ghibli style", "anime"],
        "category": "stylized",
    },
    "thangka": {
        "lora_id": "Oedon42/thangka-lora-xl",  # HuggingFace - SDXL only
        "local_path": None,  # Set to "./loras/thangka.safetensors" for local
        "name": "Tibetan Thangka Art",
        "description": "Tibetan Buddhist sacred art with intricate mandalas, deities, and spiritual symbolism (SDXL only)",
        "default_weight": 0.8,
        "weight_range": {"min": 0.0, "max": 1.2},
        "compatible_models": SDXL_COMPATIBLE_MODELS,  # SDXL only - not SD 1.5
        "trigger_words": ["thangka", "Avalokiteshvara", "bodhisattva", "tibetan art", "mandala"],
        "category": "artistic",
    },
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Model configuration
    model_id: str = "runwayml/stable-diffusion-v1-5"
    model_precision: str = "fp32"  # fp32 or fp16
    device: str = "cpu"  # cpu, cuda, or mps (Apple Silicon)

    # Generation defaults
    default_steps: int = 30
    default_guidance_scale: float = 7.5
    default_width: int = 512
    default_height: int = 512

    # Output configuration
    output_dir: str = "./generated_images"

    # Concurrency
    max_concurrent_jobs: int = 2

    # Hugging Face token (optional, required for some models)
    hf_token: str | None = None

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    def get_model_config(self, model_key: str) -> Dict[str, Any]:
        """Get model configuration by key."""
        if model_key not in MODEL_CONFIGS:
            raise ValueError(f"Unknown model key: {model_key}. Available: {', '.join(MODEL_CONFIGS.keys())}")
        return MODEL_CONFIGS[model_key]

    def get_model_id_from_key(self, model_key: str) -> str:
        """Get Hugging Face model ID from model key."""
        config = self.get_model_config(model_key)
        return config["model_id"]

    def get_lora_config(self, lora_key: str) -> Dict[str, Any]:
        """Get LoRA configuration by key.

        Args:
            lora_key: The LoRA identifier (e.g., 'thangka', 'watercolor')

        Returns:
            Dictionary containing LoRA configuration

        Raises:
            ValueError: If lora_key is not found in LORA_CONFIGS
        """
        if lora_key not in LORA_CONFIGS:
            raise ValueError(f"Unknown LoRA key: {lora_key}. Available: {', '.join(LORA_CONFIGS.keys())}")
        return LORA_CONFIGS[lora_key]

    def get_compatible_loras(self, model_key: str) -> List[str]:
        """Get list of LoRA keys compatible with a given model.

        Args:
            model_key: The model identifier (e.g., 'sd-v1-5', 'sdxl')

        Returns:
            List of LoRA keys that are compatible with the model
        """
        compatible = []
        for lora_key, lora_config in LORA_CONFIGS.items():
            if model_key in lora_config.get("compatible_models", []):
                compatible.append(lora_key)
        return compatible

    def is_lora_compatible(self, lora_key: str, model_key: str) -> bool:
        """Check if a LoRA is compatible with a specific model.

        Args:
            lora_key: The LoRA identifier
            model_key: The model identifier

        Returns:
            True if the LoRA can be used with the model, False otherwise
        """
        if lora_key not in LORA_CONFIGS:
            return False
        lora_config = LORA_CONFIGS[lora_key]
        return model_key in lora_config.get("compatible_models", [])

    def supports_inpaint(self, model_key: str) -> bool:
        """Check if a model supports inpainting.

        Args:
            model_key: The model identifier (e.g., 'sd-v1-5', 'flux-schnell')

        Returns:
            True if the model supports inpainting, False otherwise
        """
        if model_key not in MODEL_CONFIGS:
            return False
        return MODEL_CONFIGS[model_key].get("inpaint", False)

    def get_inpaint_model_id(self, model_key: str) -> str | None:
        """Get the dedicated inpainting model ID for a given base model.

        Args:
            model_key: The base model identifier (e.g., 'sd-v1-5', 'sdxl')

        Returns:
            HuggingFace model ID for the inpainting model, or None if not supported
        """
        if not self.supports_inpaint(model_key):
            return None

        # Check which inpainting model family to use
        if model_key in SD15_COMPATIBLE_MODELS:
            return INPAINT_MODEL_CONFIGS["sd15"]["model_id"]
        elif model_key in SDXL_COMPATIBLE_MODELS:
            return INPAINT_MODEL_CONFIGS["sdxl"]["model_id"]

        return None

    def get_inpaint_config(self, model_key: str) -> Dict[str, Any] | None:
        """Get the full inpainting configuration for a given base model.

        Args:
            model_key: The base model identifier

        Returns:
            Dictionary with inpainting model config, or None if not supported
        """
        if model_key in SD15_COMPATIBLE_MODELS:
            return INPAINT_MODEL_CONFIGS["sd15"]
        elif model_key in SDXL_COMPATIBLE_MODELS:
            return INPAINT_MODEL_CONFIGS["sdxl"]
        return None

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
