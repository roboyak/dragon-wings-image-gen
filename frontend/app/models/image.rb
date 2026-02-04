class Image < ApplicationRecord
  belongs_to :user
  belongs_to :parent_image, class_name: 'Image', optional: true
  has_many :child_images, class_name: 'Image', foreign_key: 'parent_image_id', dependent: :nullify

  # ActiveStorage attachment for init image (img2img)
  has_one_attached :init_image

  # Status enum
  enum status: {
    pending: 'pending',
    processing: 'processing',
    completed: 'completed',
    failed: 'failed'
  }

  # Generation type enum
  enum generation_type: {
    text_to_image: 'text_to_image',
    image_to_image: 'image_to_image',
    inpaint: 'inpaint'
  }, _prefix: true

  # Validations
  validates :prompt, presence: true, length: { minimum: 3, maximum: 1000 }
  validates :negative_prompt, length: { maximum: 1000 }, allow_blank: true
  validates :job_id, presence: true, uniqueness: true
  validates :status, presence: true, inclusion: { in: statuses.keys }
  validates :generation_type, presence: true, inclusion: { in: generation_types.keys }
  validates :num_inference_steps, numericality: { only_integer: true, greater_than: 0, less_than_or_equal_to: 150 }, allow_nil: true
  validates :guidance_scale, numericality: { greater_than: 0, less_than_or_equal_to: 20 }, allow_nil: true
  validates :width, numericality: { only_integer: true, greater_than: 0 }, allow_nil: true
  validates :height, numericality: { only_integer: true, greater_than: 0 }, allow_nil: true
  validates :strength, numericality: { greater_than_or_equal_to: 0.0, less_than_or_equal_to: 1.0 }, allow_nil: true
  validates :strength, presence: true, if: :generation_type_image_to_image?

  # Scopes
  scope :recent, -> { order(created_at: :desc) }
  scope :by_status, ->(status) { where(status: status) }
  scope :for_user, ->(user) { where(user: user) }
  scope :txt2img, -> { where(generation_type: 'text_to_image') }
  scope :img2img, -> { where(generation_type: 'image_to_image') }

  # Callbacks
  before_validation :generate_job_id, on: :create, if: -> { job_id.blank? }

  # Check if image generation is complete
  def generation_complete?
    completed? || failed?
  end

  # Check if still processing
  def processing?
    pending? || status == 'processing'
  end

  # Get display-friendly status
  def status_display
    case status
    when 'pending' then 'Queued'
    when 'processing' then 'Generating...'
    when 'completed' then 'Complete'
    when 'failed' then 'Failed'
    else 'Unknown'
    end
  end

  # Calculate generation time
  def generation_time
    return nil unless completed? && created_at && updated_at
    (updated_at - created_at).round(2)
  end

  # Calculate energy consumption in Wh
  # Formula: (65W / concurrent_images) × (generation_time_seconds / 3600)
  def energy_consumption_wh
    return nil unless generation_time && generation_time > 0

    # Default to 1 concurrent image (can be made configurable later)
    concurrent_images = 1
    base_wattage = 65.0

    power_watts = base_wattage / concurrent_images
    time_hours = generation_time / 3600.0

    (power_watts * time_hours).round(2)
  end

  # Determine energy source based on time of day
  # Returns "Solar" if generated during daylight hours, "Stored Solar" at night
  #
  # Future: Call dragon_minds_os API endpoint for real-time energy state:
  #   GET /api/energy/status => { source: "solar" | "battery" | "grid",
  #                               battery_charging: true/false,
  #                               solar_wings_deployed: true/false }
  def energy_source
    return "Solar" unless created_at

    # TODO: Replace with API call to dragon_minds_os controller
    # response = HTTP.get("http://#{dragon_mind_host}:#{port}/api/energy/status")
    # return response[:source] == "battery" ? "Stored Solar" : "Solar"

    # Simple daytime check: 6 AM to 6 PM local time
    hour = created_at.hour

    if hour >= 6 && hour < 18
      "Solar"
    else
      "Stored Solar"
    end
  end

  # Get URL for displaying image (proxied through Rails for external access)
  def display_url
    return nil unless image_url.present?
    Rails.application.routes.url_helpers.serve_image_path(self)
  end

  private

  def generate_job_id
    self.job_id = SecureRandom.uuid
  end
end
