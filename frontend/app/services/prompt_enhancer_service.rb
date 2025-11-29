# frozen_string_literal: true

# Service to enhance weak prompts with quality-boosting keywords
# Analyzes prompts and adds missing elements like style, lighting, and quality terms
class PromptEnhancerService
  # Quality keywords that indicate a well-formed prompt
  QUALITY_KEYWORDS = %w[
    detailed high-quality 4k 8k hd uhd sharp crisp
    professional masterpiece beautiful stunning
  ].freeze

  # Style keywords that indicate artistic direction
  STYLE_KEYWORDS = %w[
    photograph photo photorealistic realistic
    painting oil watercolor digital art illustration
    3d render cinema cinematic anime cartoon
    sketch drawing portrait landscape
  ].freeze

  # Lighting keywords
  LIGHTING_KEYWORDS = %w[
    lighting light lit golden hour sunset sunrise
    studio dramatic soft diffused backlit neon
    natural ambient moody dark bright
  ].freeze

  # Model-specific trigger words and enhancements
  MODEL_ENHANCEMENTS = {
    'sd-v1-5' => {
      quality_suffix: 'highly detailed, high quality',
      style_suffix: nil
    },
    'openjourney' => {
      quality_suffix: 'highly detailed, high quality',
      style_suffix: 'mdjrny-v4 style'
    },
    'sdxl' => {
      quality_suffix: 'highly detailed, masterpiece, best quality',
      style_suffix: nil
    }
  }.freeze

  class << self
    # Enhance a prompt by adding missing quality elements
    # @param prompt [String] The original user prompt
    # @param model_key [String] The model being used (sd-v1-5, openjourney, sdxl)
    # @return [String] The enhanced prompt
    def enhance(prompt, model_key = 'sd-v1-5')
      return prompt if prompt.blank?

      normalized = prompt.strip.downcase
      enhancements = []

      # Check for missing elements and add enhancements
      enhancements << quality_enhancement(normalized, model_key)
      enhancements << lighting_enhancement(normalized)
      enhancements << model_enhancement(model_key)

      # Build the enhanced prompt
      build_enhanced_prompt(prompt.strip, enhancements.compact)
    end

    # Check if a prompt would benefit from enhancement
    # @param prompt [String] The prompt to check
    # @return [Boolean] True if the prompt is weak and could be improved
    def needs_enhancement?(prompt)
      return false if prompt.blank?

      normalized = prompt.strip.downcase
      word_count = prompt.split.size

      # Short prompts almost always need enhancement
      return true if word_count < 5

      # Check for missing key elements
      missing_quality = !has_quality_keywords?(normalized)
      missing_style = !has_style_keywords?(normalized)

      # Needs enhancement if missing both quality and style
      missing_quality && missing_style
    end

    # Get a summary of what would be enhanced
    # @param prompt [String] The prompt to analyze
    # @return [Hash] Analysis of the prompt
    def analyze(prompt)
      return { empty: true } if prompt.blank?

      normalized = prompt.strip.downcase
      word_count = prompt.split.size

      {
        word_count: word_count,
        has_quality: has_quality_keywords?(normalized),
        has_style: has_style_keywords?(normalized),
        has_lighting: has_lighting_keywords?(normalized),
        needs_enhancement: needs_enhancement?(prompt),
        suggestions: build_suggestions(normalized)
      }
    end

    private

    def has_quality_keywords?(text)
      QUALITY_KEYWORDS.any? { |kw| text.include?(kw) }
    end

    def has_style_keywords?(text)
      STYLE_KEYWORDS.any? { |kw| text.include?(kw) }
    end

    def has_lighting_keywords?(text)
      LIGHTING_KEYWORDS.any? { |kw| text.include?(kw) }
    end

    def quality_enhancement(normalized, model_key)
      return nil if has_quality_keywords?(normalized)

      config = MODEL_ENHANCEMENTS[model_key] || MODEL_ENHANCEMENTS['sd-v1-5']
      config[:quality_suffix]
    end

    def lighting_enhancement(normalized)
      return nil if has_lighting_keywords?(normalized)

      'professional lighting'
    end

    def model_enhancement(model_key)
      config = MODEL_ENHANCEMENTS[model_key] || MODEL_ENHANCEMENTS['sd-v1-5']
      config[:style_suffix]
    end

    def build_enhanced_prompt(original, enhancements)
      return original if enhancements.empty?

      # Combine original with enhancements
      parts = [original] + enhancements
      parts.join(', ')
    end

    def build_suggestions(normalized)
      suggestions = []

      suggestions << 'Add quality terms (e.g., "highly detailed", "8k")' unless has_quality_keywords?(normalized)
      suggestions << 'Add style (e.g., "photograph", "oil painting")' unless has_style_keywords?(normalized)
      suggestions << 'Add lighting (e.g., "golden hour", "studio lighting")' unless has_lighting_keywords?(normalized)

      suggestions
    end
  end
end
