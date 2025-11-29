"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional
from fastapi import UploadFile


class GenerateRequest(BaseModel):
    """Request schema for image generation."""

    prompt: str = Field(..., min_length=1, max_length=1000, description="Text description of the image")
    model_key: Optional[str] = Field("sd-v1-5", description="Model key (sd-v1-5, sd-v2-1, sdxl)")
    negative_prompt: Optional[str] = Field(None, max_length=1000, description="What to avoid in the image")
    num_inference_steps: Optional[int] = Field(30, ge=10, le=100, description="Number of denoising steps")
    guidance_scale: Optional[float] = Field(7.5, ge=1.0, le=20.0, description="Prompt adherence strength")
    width: Optional[int] = Field(512, ge=256, le=1024, description="Image width (multiple of 8)")
    height: Optional[int] = Field(512, ge=256, le=1024, description="Image height (multiple of 8)")
    seed: Optional[int] = Field(None, ge=0, description="Random seed for reproducibility")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "A serene landscape with mountains and a lake at sunset, highly detailed, 4k",
                "negative_prompt": "blurry, low quality, distorted",
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
                "width": 512,
                "height": 512,
                "seed": 42,
            }
        }


class Img2ImgRequest(BaseModel):
    """Request schema for image-to-image generation.

    Note: This schema is used for documentation only.
    Actual endpoint uses Form parameters due to file upload.
    """

    prompt: str = Field(..., min_length=1, max_length=1000, description="Text description of desired transformation")
    model_key: Optional[str] = Field("sd-v1-5", description="Model key (sd-v1-5, sd-v2-1, sdxl)")
    negative_prompt: Optional[str] = Field(None, max_length=1000, description="What to avoid in the image")
    strength: Optional[float] = Field(0.75, ge=0.0, le=1.0, description="Transformation strength (0.0=keep original, 1.0=complete transform)")
    num_inference_steps: Optional[int] = Field(50, ge=10, le=100, description="Number of denoising steps")
    guidance_scale: Optional[float] = Field(7.5, ge=1.0, le=20.0, description="Prompt adherence strength")
    seed: Optional[int] = Field(None, ge=0, description="Random seed for reproducibility")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Turn this into a watercolor painting, soft colors, artistic",
                "negative_prompt": "blurry, low quality, photograph",
                "strength": 0.75,
                "num_inference_steps": 50,
                "guidance_scale": 7.5,
                "seed": 42,
            }
        }


class GenerateResponse(BaseModel):
    """Response schema for successful image generation."""

    job_id: str = Field(..., description="Unique identifier for this generation job")
    status: str = Field(..., description="Job status: pending, processing, completed, failed")
    image_url: Optional[str] = Field(None, description="URL to the generated image (when completed)")
    image_base64: Optional[str] = Field(None, description="Base64-encoded image data (when completed)")
    message: Optional[str] = Field(None, description="Status message or error description")
    generation_time: Optional[float] = Field(None, description="Time taken to generate image in seconds")


class StatusResponse(BaseModel):
    """Response schema for job status check."""

    job_id: str
    status: str
    image_url: Optional[str] = None
    message: Optional[str] = None
    generation_time: Optional[float] = None
    progress_percent: Optional[float] = Field(None, description="Generation progress 0-100")


class HealthResponse(BaseModel):
    """Response schema for health check."""

    status: str = Field(..., description="Service status: healthy, degraded, unhealthy")
    model_loaded: bool = Field(..., description="Whether the SD model is loaded")
    model_id: str = Field(..., description="Currently configured model")
    device: str = Field(..., description="Device being used (cpu, cuda, mps)")
    version: str = Field(..., description="API version")


class ErrorResponse(BaseModel):
    """Response schema for errors."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(None, description="Additional error details")
