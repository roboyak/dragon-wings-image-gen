class StableDiffusionService
  include HTTParty
  base_uri ENV.fetch('STABLE_DIFFUSION_API_URL', 'http://localhost:8000')

  class ServiceError < StandardError; end
  class GenerationError < ServiceError; end
  class StatusCheckError < ServiceError; end

  # Generate a new image (text-to-image)
  def self.generate(prompt:, model_key: 'sd-v1-5', negative_prompt: nil, num_inference_steps: 30, guidance_scale: 7.5, width: 512, height: 512, loras: nil)
    body = {
      prompt: prompt,
      model_key: model_key,
      negative_prompt: negative_prompt || "",
      num_inference_steps: num_inference_steps,
      guidance_scale: guidance_scale,
      width: width,
      height: height
    }

    # Add LoRA specs if provided (array of {key:, weight:} hashes)
    if loras.present?
      body[:loras] = loras.map { |l| { key: l[:key], weight: l[:weight]&.to_f } }
    end

    response = post(
      '/api/generate',
      body: body.to_json,
      headers: { 'Content-Type' => 'application/json' },
      timeout: 10
    )

    if response.success?
      response.parsed_response
    else
      raise GenerationError, "Failed to start generation: #{response.code} - #{response.message}"
    end
  rescue HTTParty::Error, Timeout::Error => e
    raise GenerationError, "API request failed: #{e.message}"
  end

  # Generate image from image (image-to-image)
  def self.generate_img2img(init_image_file:, prompt:, model_key: 'sd-v1-5', negative_prompt: nil, strength: 0.75, num_inference_steps: 50, guidance_scale: 7.5, seed: nil)
    # Build multipart form data
    # HTTParty requires multipart gem for file uploads
    require 'net/http'
    require 'uri'

    uri = URI.parse("#{base_uri}/api/generate_img2img")

    # Create multipart form data manually
    boundary = "----WebKitFormBoundary#{SecureRandom.hex(16)}"
    post_body = []

    # Add file (sanitize filename - replace spaces and special chars)
    safe_filename = init_image_file.original_filename.gsub(/[^a-zA-Z0-9._-]/, '_')
    post_body << "--#{boundary}\r\n"
    post_body << "Content-Disposition: form-data; name=\"init_image\"; filename=\"#{safe_filename}\"\r\n"
    post_body << "Content-Type: #{init_image_file.content_type}\r\n\r\n"
    post_body << init_image_file.read
    post_body << "\r\n"

    # Add form fields
    form_data = {
      'prompt' => prompt,
      'model_key' => model_key,
      'negative_prompt' => negative_prompt || "",
      'strength' => strength.to_s,
      'num_inference_steps' => num_inference_steps.to_s,
      'guidance_scale' => guidance_scale.to_s
    }
    form_data['seed'] = seed.to_s if seed.present?

    form_data.each do |key, value|
      post_body << "--#{boundary}\r\n"
      post_body << "Content-Disposition: form-data; name=\"#{key}\"\r\n\r\n"
      post_body << value
      post_body << "\r\n"
    end

    post_body << "--#{boundary}--\r\n"

    # Make request
    http = Net::HTTP.new(uri.host, uri.port)
    http.read_timeout = 10

    request = Net::HTTP::Post.new(uri.request_uri)
    request.body = post_body.join
    request['Content-Type'] = "multipart/form-data; boundary=#{boundary}"

    response = http.request(request)

    if response.code.to_i == 200
      JSON.parse(response.body)
    else
      raise GenerationError, "Failed to start img2img generation: #{response.code} - #{response.message}"
    end
  rescue StandardError => e
    raise GenerationError, "Img2img API request failed: #{e.message}"
  end

  # Generate image with inpainting (selective region editing)
  def self.generate_inpaint(init_image_url:, mask_data:, prompt:, model_key: 'sd-v1-5', negative_prompt: nil, strength: 0.8, num_inference_steps: 30, guidance_scale: 7.5, blur_mask: true, blur_factor: 33, seed: nil, loras: nil)
    require 'net/http'
    require 'uri'
    require 'base64'

    uri = URI.parse("#{base_uri}/api/generate_inpaint")

    # Download the original image from URL
    init_image_uri = URI.parse(init_image_url)
    init_image_response = Net::HTTP.get_response(init_image_uri)
    raise GenerationError, "Failed to download init image" unless init_image_response.is_a?(Net::HTTPSuccess)
    init_image_data = init_image_response.body

    # Decode mask from base64 data URL
    # Format: "data:image/png;base64,iVBORw0KGgo..."
    mask_base64 = mask_data.sub(/^data:image\/\w+;base64,/, '')
    mask_image_data = Base64.decode64(mask_base64)

    # Create multipart form data
    boundary = "----WebKitFormBoundary#{SecureRandom.hex(16)}"
    post_body = []

    # Add init_image file (sanitized filename)
    post_body << "--#{boundary}\r\n"
    post_body << "Content-Disposition: form-data; name=\"init_image\"; filename=\"init_image.png\"\r\n"
    post_body << "Content-Type: image/png\r\n\r\n"
    post_body << init_image_data
    post_body << "\r\n"

    # Add mask_image file (sanitized filename)
    post_body << "--#{boundary}\r\n"
    post_body << "Content-Disposition: form-data; name=\"mask_image\"; filename=\"mask_image.png\"\r\n"
    post_body << "Content-Type: image/png\r\n\r\n"
    post_body << mask_image_data
    post_body << "\r\n"

    # Add form fields
    form_data = {
      'prompt' => prompt,
      'model_key' => model_key,
      'negative_prompt' => negative_prompt || "",
      'strength' => strength.to_s,
      'num_inference_steps' => num_inference_steps.to_s,
      'guidance_scale' => guidance_scale.to_s,
      'blur_mask' => blur_mask.to_s,
      'blur_factor' => blur_factor.to_s
    }
    form_data['seed'] = seed.to_s if seed.present?

    # Add LoRAs if present (as JSON array)
    if loras.present?
      form_data['loras'] = loras.to_json
    end

    form_data.each do |key, value|
      post_body << "--#{boundary}\r\n"
      post_body << "Content-Disposition: form-data; name=\"#{key}\"\r\n\r\n"
      post_body << value
      post_body << "\r\n"
    end

    post_body << "--#{boundary}--\r\n"

    # Make request
    http = Net::HTTP.new(uri.host, uri.port)
    http.read_timeout = 10

    request = Net::HTTP::Post.new(uri.request_uri)
    request.body = post_body.join
    request['Content-Type'] = "multipart/form-data; boundary=#{boundary}"

    response = http.request(request)

    if response.code.to_i == 200
      JSON.parse(response.body)
    else
      error_msg = begin
        JSON.parse(response.body)['detail'] || response.message
      rescue
        response.message
      end
      raise GenerationError, "Failed to start inpaint generation: #{response.code} - #{error_msg}"
    end
  rescue StandardError => e
    raise GenerationError, "Inpaint API request failed: #{e.message}"
  end

  # Check status of a generation job
  def self.check_status(job_id)
    response = get(
      "/api/status/#{job_id}",
      timeout: 5
    )

    if response.success?
      data = response.parsed_response
      # Fix image URL to include backend host
      if data['image_url'] && !data['image_url'].start_with?('http')
        data['image_url'] = "#{base_uri}#{data['image_url']}"
      end
      data
    else
      raise StatusCheckError, "Failed to check status: #{response.code} - #{response.message}"
    end
  rescue HTTParty::Error, Timeout::Error => e
    raise StatusCheckError, "Status check failed: #{e.message}"
  end

  # Health check
  def self.healthy?
    response = get('/api/health', timeout: 3)
    response.success? && response.parsed_response['status'] == 'healthy'
  rescue
    false
  end

  # Get available models
  def self.models
    response = get('/api/models', timeout: 3)
    response.success? ? response.parsed_response : []
  rescue
    []
  end
end
