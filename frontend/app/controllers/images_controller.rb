class ImagesController < ApplicationController
  before_action :authenticate_user!
  before_action :set_image, only: [:show, :status, :toggle_favorite, :edit_mask, :generate_inpaint]
  before_action :check_quota, only: [:create]

  # GET /images
  def index
    # Support view filters via query params (Phase 4C: Gallery/History views)
    base_query = current_user.images

    case params[:view]
    when 'gallery'
      # Gallery: Show only successful/completed images
      @images = base_query.where(status: 'completed').recent
      @view_mode = 'gallery'
    when 'history'
      # History: Show ALL images (including failed/generating)
      @images = base_query.recent
      @view_mode = 'history'
    when 'favorites'
      # Favorites: Show only favorited images
      @images = base_query.where(favorite: true).recent
      @view_mode = 'favorites'
    else
      # Default: Show all recent images
      @images = base_query.recent
      @view_mode = 'all'
    end

    @pending_images = current_user.images.where(status: ['pending', 'processing']).recent
  end

  # POST /images
  def create
    # Get batch size (default: 1)
    batch_size = params[:batch_size]&.to_i || 1
    batch_size = batch_size.clamp(1, 4) # Limit to max 4

    # Determine generation mode
    generation_mode = params[:generation_mode] || 'text_to_image'

    # Get base seed (for incremental batch seeds)
    base_seed = params[:seed]&.to_i

    @images = []
    batch_size.times do |i|
      @image = current_user.images.new(image_params)
      @image.generation_type = generation_mode

      # Calculate seed for this batch item
      if base_seed
        @image.seed = base_seed + i
      else
        # Let backend generate random seeds
        @image.seed = nil
      end

      begin
        Rails.logger.info "=== CALLING STABLE DIFFUSION API (#{generation_mode}) [Batch #{i+1}/#{batch_size}] ==="

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
        # Parse LoRA params if present
        loras = parse_lora_params

        api_response = StableDiffusionService.generate(
          prompt: @image.prompt,
          model_key: @image.model_key || 'sd-v1-5',
          negative_prompt: @image.negative_prompt,
          num_inference_steps: @image.num_inference_steps || 30,
          guidance_scale: @image.guidance_scale || 7.5,
          width: @image.width || 512,
          height: @image.height || 512,
          seed: @image.seed,
          loras: loras
        )
      end

      Rails.logger.info "=== API RESPONSE: #{api_response.inspect} ==="

      # Update image with job ID and seed from API
      @image.job_id = api_response['job_id']
      @image.status = api_response['status'] || 'pending'
      @image.seed = api_response['seed'] if api_response['seed'] # Store actual seed used
      Rails.logger.info "=== SET JOB_ID: #{@image.job_id}, SEED: #{@image.seed} ==="

      if @image.save
        @images << @image
        Rails.logger.info "=== Batch item #{i+1}/#{batch_size} saved with ID: #{@image.id} ==="
      else
        Rails.logger.error "=== Failed to save batch item #{i+1}: #{@image.errors.full_messages} ==="
      end

      rescue StableDiffusionService::GenerationError => e
        Rails.logger.error "=== GENERATION ERROR (batch #{i+1}): #{e.message} ==="
        @image.status = 'failed'
        @image.metadata = { error: e.message }
        @image.save(validate: false)
        @images << @image
      end
    end

    # Increment user's generation counter by batch size
    current_user.increment_generations!(batch_size)

    # Respond with batch results
    respond_to do |format|
      if @images.any? && @images.all?(&:persisted?)
        notice_text = batch_size > 1 ? "Started generating #{batch_size} images!" : 'Image generation started!'
        format.html { redirect_to images_path, notice: notice_text }
        format.json { render json: @images, status: :created }
      else
        format.html { redirect_to images_path, alert: 'Failed to start generation' }
        format.json { render json: { errors: @images.map(&:errors) }, status: :unprocessable_entity }
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

  # POST /images/:id/toggle_favorite
  def toggle_favorite
    @image.update(favorite: !@image.favorite)

    respond_to do |format|
      format.html { redirect_back fallback_location: images_path }
      format.json { render json: { id: @image.id, favorite: @image.favorite } }
    end
  end

  # GET /images/:id/edit_mask
  # Mask editor page for inpainting
  def edit_mask
    unless @image.generation_complete?
      redirect_to @image, alert: "Cannot edit mask for incomplete image"
      return
    end

    # Check if model supports inpainting
    @supports_inpaint = model_supports_inpaint?(@image.model_key)
    @available_models = available_inpaint_models
  end

  # POST /images/:id/generate_inpaint
  # Generate new image using mask
  def generate_inpaint
    unless params[:mask_data].present?
      render json: { error: 'Mask data is required' }, status: :unprocessable_entity
      return
    end

    begin
      # Create new image record for the inpainted result
      @new_image = current_user.images.new(
        prompt: params[:prompt],
        negative_prompt: params[:negative_prompt],
        model_key: params[:model_key] || @image.model_key,
        num_inference_steps: params[:num_inference_steps]&.to_i || 30,
        guidance_scale: params[:guidance_scale]&.to_f || 7.5,
        generation_type: 'inpaint',
        parent_image_id: @image.id
      )

      # Parse LoRA params
      loras = parse_inpaint_lora_params

      # Call backend inpainting API
      api_response = StableDiffusionService.generate_inpaint(
        init_image_url: @image.image_url,
        mask_data: params[:mask_data],
        prompt: params[:prompt],
        model_key: params[:model_key] || @image.model_key,
        negative_prompt: params[:negative_prompt],
        strength: params[:strength]&.to_f || 0.8,
        num_inference_steps: params[:num_inference_steps]&.to_i || 30,
        guidance_scale: params[:guidance_scale]&.to_f || 7.5,
        blur_mask: params[:blur_mask] != 'false',
        blur_factor: params[:blur_factor]&.to_i || 33,
        seed: params[:seed]&.to_i,
        loras: loras
      )

      @new_image.job_id = api_response['job_id']
      @new_image.status = api_response['status'] || 'pending'

      if @new_image.save
        current_user.increment_generations!
        render json: {
          id: @new_image.id,
          job_id: @new_image.job_id,
          status: @new_image.status,
          status_url: status_image_path(@new_image)
        }, status: :created
      else
        render json: { error: @new_image.errors.full_messages.join(', ') }, status: :unprocessable_entity
      end

    rescue StableDiffusionService::GenerationError => e
      Rails.logger.error "=== INPAINT ERROR: #{e.message} ==="
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

  # Parse LoRA params from form submission
  # Supports both single lora_key and multiple loras[] array
  def parse_lora_params
    loras = []

    # Handle array format: loras[][key], loras[][weight]
    if params[:loras].present? && params[:loras].is_a?(Array)
      params[:loras].each do |lora|
        next unless lora[:key].present?
        loras << {
          key: lora[:key],
          weight: lora[:weight]&.to_f || 0.8
        }
      end
    # Handle simple single lora_key format (backwards compatible)
    elsif params.dig(:image, :lora_key).present?
      lora_key = params[:image][:lora_key]
      lora_weight = params.dig(:image, :lora_weight)&.to_f || 0.8
      loras << { key: lora_key, weight: lora_weight }
    end

    loras.presence # Return nil if empty
  end

  # Parse LoRA params from inpainting form
  def parse_inpaint_lora_params
    loras = []
    if params[:loras].present? && params[:loras].is_a?(Array)
      params[:loras].each do |lora|
        next unless lora[:key].present?
        loras << {
          key: lora[:key],
          weight: lora[:weight]&.to_f || 0.8
        }
      end
    end
    loras.presence
  end

  # Check if a model supports inpainting
  def model_supports_inpaint?(model_key)
    # Models that support inpainting (SD 1.5 based and SDXL)
    %w[sd-v1-5 openjourney sdxl realistic-vision dreamshaper analog-diffusion].include?(model_key)
  end

  # Get list of models that support inpainting
  def available_inpaint_models
    [
      { key: 'sd-v1-5', name: 'Stable Diffusion v1.5' },
      { key: 'openjourney', name: 'OpenJourney' },
      { key: 'sdxl', name: 'Stable Diffusion XL' },
      { key: 'realistic-vision', name: 'Realistic Vision v5.1' },
      { key: 'dreamshaper', name: 'DreamShaper 8' },
      { key: 'analog-diffusion', name: 'Analog Diffusion' }
    ]
  end
end
