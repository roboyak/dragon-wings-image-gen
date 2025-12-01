class ModelsController < ApplicationController
  before_action :authenticate_user!

  def index
    # Model data - matches backend/app/config.py
    @models = [
      {
        key: "sd-v1-5",
        name: "Stable Diffusion v1.5",
        category: "General Purpose",
        description: "Fast, lightweight, general-purpose model",
        resolution: "512×512",
        ram: "4 GB",
        recommended_for: "General use, fast generation, limited hardware",
        strengths: ["Speed", "Low memory usage", "General objects"],
        weaknesses: ["Limited artistic styles", "Lower quality details"],
        supports_img2img: true
      },
      {
        key: "openjourney",
        name: "OpenJourney",
        category: "Artistic",
        description: "Midjourney-style artistic images",
        resolution: "512×512",
        ram: "4 GB",
        recommended_for: "Artistic, stylized images with Midjourney aesthetic",
        strengths: ["Artistic style", "Beautiful renders", "No license required"],
        weaknesses: ["Less photorealistic", "Specific style"],
        supports_img2img: true
      },
      {
        key: "realistic-vision",
        name: "Realistic Vision v5.1",
        category: "Photorealistic",
        description: "Photorealistic portraits and scenes",
        resolution: "512×512",
        ram: "4 GB",
        recommended_for: "Photorealistic images, portraits, natural scenes",
        strengths: ["Photorealism", "Portraits", "Skin textures", "Natural lighting"],
        weaknesses: ["Less artistic/stylized", "Can look too perfect"],
        supports_img2img: true
      },
      {
        key: "dreamshaper",
        name: "DreamShaper 8",
        category: "Fantasy",
        description: "Fantasy and artistic illustrations",
        resolution: "512×512",
        ram: "4 GB",
        recommended_for: "Fantasy art, illustrations, stylized portraits",
        strengths: ["Artistic style", "Fantasy themes", "Beautiful colors", "Detailed backgrounds"],
        weaknesses: ["Less photorealistic", "Specific artistic style"],
        supports_img2img: true
      },
      {
        key: "analog-diffusion",
        name: "Analog Diffusion",
        category: "Vintage",
        description: "Vintage film photography aesthetic",
        resolution: "512×512",
        ram: "4 GB",
        recommended_for: "Film photography look, vintage aesthetic, nostalgic images",
        strengths: ["Film grain", "Vintage colors", "Nostalgic mood", "Natural imperfections"],
        weaknesses: ["Specific style only", "Requires 'analog style' in prompt"],
        supports_img2img: true
      },
      {
        key: "sdxl",
        name: "Stable Diffusion XL",
        category: "Premium",
        description: "Highest quality, excellent artistic style transfer",
        resolution: "1024×1024",
        ram: "12 GB",
        recommended_for: "Professional quality, artistic transformations",
        strengths: ["Exceptional quality", "Artistic styles", "High resolution", "Detail preservation"],
        weaknesses: ["Slower generation", "High memory usage", "Requires GPU"],
        supports_img2img: true,
        requires_gpu: true
      },
      {
        key: "flux-schnell",
        name: "FLUX.1 Schnell",
        category: "Next-Gen",
        description: "State-of-art quality, excellent text rendering",
        resolution: "1024×1024",
        ram: "12 GB",
        recommended_for: "High quality images, text in images, professional results",
        strengths: ["Best quality", "Text rendering", "Prompt following", "Fast for quality"],
        weaknesses: ["Large model (~12GB)", "No img2img support"],
        supports_img2img: false,
        next_gen: true
      }
    ]
  end
end
