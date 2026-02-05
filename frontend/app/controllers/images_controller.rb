class ImagesController < ApplicationController
  before_action :authenticate_user!
  before_action :set_image, only: [:show, :status, :toggle_favorite, :edit_mask, :generate_inpaint, :download, :serve, :destroy]
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
          loras: loras
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

  # GET /images/:id/download
  # Server-side download endpoint that fetches image from backend and serves with proper headers
  def download
    # Validate image is complete and has image_url
    unless @image.completed?
      redirect_to @image, alert: "Image is not ready for download yet (status: #{@image.status_display})"
      return
    end

    unless @image.image_url.present?
      redirect_to @image, alert: "Image URL is not available"
      return
    end

    begin
      # Fetch JPEG version (with EXIF metadata) instead of PNG
      # Free tier gets watermarked version, paid tiers get clean version
      if current_user.free?
        jpeg_url = @image.image_url.sub('.png', '_watermark.jpg')
      else
        jpeg_url = @image.image_url.sub('.png', '.jpg')
      end

      response = HTTParty.get(
        jpeg_url,
        timeout: 30,
        follow_redirects: true
      )

      # If watermarked version not found (old images), fall back to clean version
      if response.code == 404 && current_user.free?
        Rails.logger.info "=== Watermarked version not found, falling back to clean JPEG ==="
        jpeg_url = @image.image_url.sub('.png', '.jpg')
        response = HTTParty.get(jpeg_url, timeout: 30, follow_redirects: true)
      end

      # Check if request was successful
      unless response.success?
        Rails.logger.error "=== DOWNLOAD ERROR: HTTP #{response.code} from #{jpeg_url} ==="
        redirect_to @image, alert: "Failed to download image (HTTP #{response.code})"
        return
      end

      # Send the JPEG image data with EXIF metadata
      send_data response.body,
                type: 'image/jpeg',
                disposition: 'attachment',
                filename: "dragon-wings-#{@image.id}.jpg"

    rescue HTTParty::Error, Net::OpenTimeout, Net::ReadTimeout => e
      Rails.logger.error "=== DOWNLOAD ERROR: #{e.class} - #{e.message} ==="
      Rails.logger.error e.backtrace.join("\n")
      redirect_to @image, alert: "Failed to download image: Backend unavailable"
    rescue StandardError => e
      Rails.logger.error "=== UNEXPECTED DOWNLOAD ERROR: #{e.class} - #{e.message} ==="
      Rails.logger.error e.backtrace.join("\n")
      redirect_to @image, alert: "Failed to download image: #{e.message}"
    end
  end

  # DELETE /images/:id
  def destroy
    @image.destroy
    redirect_to images_path, notice: "Image deleted successfully"
  end

  # Serve image inline through Rails (for ngrok/external access)
  def serve
    unless @image.completed?
      head :not_found
      return
    end

    unless @image.image_url.present?
      head :not_found
      return
    end

    begin
      # Fetch image from backend
      response = HTTParty.get(
        @image.image_url,
        timeout: 30,
        follow_redirects: true
      )

      unless response.success?
        Rails.logger.error "=== SERVE ERROR: HTTP #{response.code} from #{@image.image_url} ==="
        head :not_found
        return
      end

      # Send the image data inline for display
      send_data response.body,
                type: 'image/png',
                disposition: 'inline'

    rescue StandardError => e
      Rails.logger.error "=== SERVE ERROR: #{e.class} - #{e.message} ==="
      head :not_found
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
      :strength,
      :lora_key
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
