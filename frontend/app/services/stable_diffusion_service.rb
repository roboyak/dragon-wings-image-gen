class StableDiffusionService
  include HTTParty
  base_uri ENV.fetch('STABLE_DIFFUSION_API_URL', 'http://localhost:8000')

  class ServiceError < StandardError; end
  class GenerationError < ServiceError; end
  class StatusCheckError < ServiceError; end

  # Generate a new image
  def self.generate(prompt:, negative_prompt: nil, num_inference_steps: 30, guidance_scale: 7.5, width: 512, height: 512)
    response = post(
      '/api/generate',
      body: {
        prompt: prompt,
        negative_prompt: negative_prompt || "",
        num_inference_steps: num_inference_steps,
        guidance_scale: guidance_scale,
        width: width,
        height: height
      }.to_json,
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
