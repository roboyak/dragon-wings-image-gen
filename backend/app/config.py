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
        "prompt_suffix": "analog style",
    },
    "flux-schnell": {
        "model_id": "black-forest-labs/FLUX.1-schnell",
        "name": "FLUX.1 Schnell",
        "description": "State-of-art quality, excellent text rendering, fast generation",
        "native_resolution": 1024,
        "recommended_for": "High quality images, text in images, professional results",
        "strengths": ["Best quality", "Text rendering", "Prompt following", "Fast for its quality"],
        "weaknesses": ["Large model (~12GB)", "Higher memory usage"],
        "ram_required_gb": 12,
        "txt2img": True,
        "img2img": False,
        "pipeline_type": "flux",
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

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
