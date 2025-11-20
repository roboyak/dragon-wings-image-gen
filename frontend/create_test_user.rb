user = User.create!(
  email: 'admin@dragonwings.ai',
  password: 'dragonwings123',
  password_confirmation: 'dragonwings123',
  subscription_tier: :enterprise
)

puts "✅ Test user created successfully!"
puts "   Email: #{user.email}"
puts "   Password: dragonwings123"
puts "   Tier: #{user.tier_display_name}"
puts "   Quota: #{user.generation_quota} generations/day"
