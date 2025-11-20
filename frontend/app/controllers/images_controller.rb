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

    begin
      # Call Stable Diffusion API to start generation
      Rails.logger.info "=== CALLING STABLE DIFFUSION API ==="
      api_response = StableDiffusionService.generate(
        prompt: @image.prompt,
        negative_prompt: @image.negative_prompt,
        num_inference_steps: @image.num_inference_steps || 30,
        guidance_scale: @image.guidance_scale || 7.5,
        width: @image.width || 512,
        height: @image.height || 512
      )
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

      render json: {
        id: @image.id,
        status: @image.status,
        status_display: @image.status_display,
        image_url: @image.image_url,
        generation_complete: @image.generation_complete?,
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
      :num_inference_steps,
      :guidance_scale,
      :width,
      :height,
      :seed
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
