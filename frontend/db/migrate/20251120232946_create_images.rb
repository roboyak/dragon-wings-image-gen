class CreateImages < ActiveRecord::Migration[7.1]
  def change
    create_table :images do |t|
      t.references :user, null: false, foreign_key: true
      t.text :prompt, null: false
      t.text :negative_prompt
      t.string :status, null: false, default: 'pending'
      t.string :job_id, null: false
      t.string :image_url
      t.integer :num_inference_steps, default: 30
      t.decimal :guidance_scale, precision: 3, scale: 1, default: 7.5
      t.integer :width, default: 512
      t.integer :height, default: 512
      t.integer :seed
      t.jsonb :metadata, default: {}

      t.timestamps
    end

    add_index :images, :job_id, unique: true
    add_index :images, :status
    add_index :images, [:user_id, :created_at]
  end
end
