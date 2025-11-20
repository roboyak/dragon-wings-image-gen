class Image < ApplicationRecord
  belongs_to :user

  # Status enum
  enum status: {
    pending: 'pending',
    processing: 'processing',
    completed: 'completed',
    failed: 'failed'
  }

  # Validations
  validates :prompt, presence: true, length: { minimum: 3, maximum: 1000 }
  validates :negative_prompt, length: { maximum: 1000 }, allow_blank: true
  validates :job_id, presence: true, uniqueness: true
  validates :status, presence: true, inclusion: { in: statuses.keys }
  validates :num_inference_steps, numericality: { only_integer: true, greater_than: 0, less_than_or_equal_to: 150 }, allow_nil: true
  validates :guidance_scale, numericality: { greater_than: 0, less_than_or_equal_to: 20 }, allow_nil: true
  validates :width, numericality: { only_integer: true, greater_than: 0 }, allow_nil: true
  validates :height, numericality: { only_integer: true, greater_than: 0 }, allow_nil: true

  # Scopes
  scope :recent, -> { order(created_at: :desc) }
  scope :by_status, ->(status) { where(status: status) }
  scope :for_user, ->(user) { where(user: user) }

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

  private

  def generate_job_id
    self.job_id = SecureRandom.uuid
  end
end
