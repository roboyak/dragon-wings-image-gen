class ImagesController < ApplicationController
  before_action :authenticate_user!
  before_action :set_image, only: [:show, :status]
  before_action :check_quota, only: [:create]

  # GET /images
  def index
    @images = current_user.images.recent
    @pending_images = current_user.images.where(status: ['pending', 'processing']).recent
  end

  # POST /images
  def create
    @image = current_user.images.new(image_params)

    # Determine generation mode
    generation_mode = params[:generation_mode] || 'text_to_image'
    @image.generation_type = generation_mode

    begin
      Rails.logger.info "=== CALLING STABLE DIFFUSION API (#{generation_mode}) ==="

      if generation_mode == 'image_to_image'
        # Image-to-image generation
        unless params[:init_image].present?
          raise StableDiffusionService::GenerationError, "Initial image is required for img2img generation"
        end

        # Store init image with ActiveStorage
        @image.init_image.attach(params[:init_image])
        @image.strength = params[:strength]&.to_f || 0.75

        api_response = StableDiffusionService.generate_img2img(
          init_image_file: params[:init_image],
          prompt: @image.prompt,
          model_key: @image.model_key || 'sd-v1-5',
          negative_prompt: @image.negative_prompt,
          strength: @image.strength,
          num_inference_steps: @image.num_inference_steps || 50,
          guidance_scale: @image.guidance_scale || 7.5,
          seed: @image.seed
        )
      else
        # Text-to-image generation (default)
        api_response = StableDiffusionService.generate(
          prompt: @image.prompt,
          model_key: @image.model_key || 'sd-v1-5',
          negative_prompt: @image.negative_prompt,
          num_inference_steps: @image.num_inference_steps || 30,
          guidance_scale: @image.guidance_scale || 7.5,
          width: @image.width || 512,
          height: @image.height || 512
        )
      end

      Rails.logger.info "=== API RESPONSE: #{api_response.inspect} ==="

      # Update image with job ID from API
      @image.job_id = api_response['job_id']
      @image.status = api_response['status'] || 'pending'
      Rails.logger.info "=== SET JOB_ID: #{@image.job_id} ==="

      if @image.save
        # Increment user's generation counter
        current_user.increment_generations!

        respond_to do |format|
          format.html { redirect_to images_path, notice: 'Image generation started!' }
          format.json { render json: @image, status: :created }
        end
      else
        respond_to do |format|
          format.html { render :index, status: :unprocessable_entity }
          format.json { render json: @image.errors, status: :unprocessable_entity }
        end
      end

    rescue StableDiffusionService::GenerationError => e
      Rails.logger.error "=== GENERATION ERROR: #{e.message} ==="
      Rails.logger.error e.backtrace.join("\n")
      @image.status = 'failed'
      @image.metadata = { error: e.message }
      @image.save(validate: false) if @image.job_id.present?

      respond_to do |format|
        format.html { redirect_to images_path, alert: "Generation failed: #{e.message}" }
        format.json { render json: { error: e.message }, status: :service_unavailable }
      end
    end
  end

  # GET /images/:id
  def show
    @image = current_user.images.find(params[:id])
  end

  # POST /images/enhance_prompt
  # AJAX endpoint to enhance a weak prompt with quality keywords
  def enhance_prompt
    prompt = params[:prompt].to_s.strip
    model_key = params[:model_key] || 'sd-v1-5'

    if prompt.blank?
      render json: { error: 'Prompt is required' }, status: :unprocessable_entity
      return
    end

    analysis = PromptEnhancerService.analyze(prompt)
    enhanced = PromptEnhancerService.enhance(prompt, model_key)

    render json: {
      original: prompt,
      enhanced: enhanced,
      was_enhanced: prompt != enhanced,
      analysis: analysis
    }
  end

  # GET /images/:id/status
  def status
    begin
      # Check status from Stable Diffusion API
      api_status = StableDiffusionService.check_status(@image.job_id)

      # Update image with latest status
      @image.update(
        status: api_status['status'],
        image_url: api_status['image_url'],
        metadata: api_status.except('status', 'job_id', 'image_url')
      )

      # Use the real progress_percent from the backend API
      progress_percent = api_status['progress_percent']

      render json: {
        id: @image.id,
        status: @image.status,
        status_display: @image.status_display,
        image_url: @image.image_url,
        generation_complete: @image.generation_complete?,
        progress_percent: progress_percent,
        created_at: @image.created_at,
        updated_at: @image.updated_at
      }

    rescue StableDiffusionService::StatusCheckError => e
      render json: { error: e.message }, status: :service_unavailable
    end
  end

  private

  def set_image
    @image = current_user.images.find(params[:id])
  end

  def image_params
    params.require(:image).permit(
      :prompt,
      :negative_prompt,
      :model_key,
      :num_inference_steps,
      :guidance_scale,
      :width,
      :height,
      :seed,
      :generation_type,
      :strength
    )
  end

  def check_quota
    unless current_user.can_generate?
      respond_to do |format|
        format.html { redirect_to images_path, alert: "Daily quota exceeded! You've used #{current_user.generations_today}/#{current_user.generation_quota} generations today." }
        format.json { render json: { error: 'Quota exceeded' }, status: :forbidden }
      end
    end
  end
end
