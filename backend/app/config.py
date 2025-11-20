"""Configuration management for the backend."""
from pydantic_settings import BaseSettings
from typing import List


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

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
