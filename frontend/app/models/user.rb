class User < ApplicationRecord
  # Include default devise modules. Others available are:
  # :confirmable, :lockable, :timeoutable, :trackable and :omniauthable
  devise :database_authenticatable, :registerable,
         :recoverable, :rememberable, :validatable

  # Associations
  has_many :images, dependent: :destroy

  # Subscription tiers with generation quotas
  enum subscription_tier: {
    free: 0,
    maker: 1,
    pro: 2,
    enterprise: 3
  }

  # Quota limits per tier
  TIER_QUOTAS = {
    free: 10,
    maker: 50,
    pro: 200,
    enterprise: 1000
  }.freeze

  # Set generation quota based on tier
  before_validation :set_generation_quota, on: :create
  before_save :update_quota_on_tier_change, if: :subscription_tier_changed?

  # Check if user can generate images
  def can_generate?
    generations_today < generation_quota
  end

  # Increment generation counter (supports batch generation)
  def increment_generations!(count = 1)
    reset_quota_if_needed
    update!(generations_today: generations_today + count)
  end

  # Reset quota if date changed
  def reset_quota_if_needed
    if quota_reset_date.nil? || quota_reset_date < Date.today
      update!(generations_today: 0, quota_reset_date: Date.today)
    end
  end

  # Human-readable tier name
  def tier_display_name
    subscription_tier.titleize
  end

  private

  def set_generation_quota
    self.generation_quota = TIER_QUOTAS[subscription_tier.to_sym]
    self.quota_reset_date = Date.today
  end

  def update_quota_on_tier_change
    self.generation_quota = TIER_QUOTAS[subscription_tier.to_sym]
  end
end
