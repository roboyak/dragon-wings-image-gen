# This file is auto-generated from the current state of the database. Instead
# of editing this file, please use the migrations feature of Active Record to
# incrementally modify your database, and then regenerate this schema definition.
#
# This file is the source Rails uses to define your schema when running `bin/rails
# db:schema:load`. When creating a new database, `bin/rails db:schema:load` tends to
# be faster and is potentially less error prone than running all of your
# migrations from scratch. Old migrations may fail to apply correctly if those
# migrations use external dependencies or application code.
#
# It's strongly recommended that you check this file into your version control system.

ActiveRecord::Schema[7.1].define(version: 2025_11_20_232946) do
  # These are extensions that must be enabled in order to support this database
  enable_extension "plpgsql"

  create_table "images", force: :cascade do |t|
    t.bigint "user_id", null: false
    t.text "prompt", null: false
    t.text "negative_prompt"
    t.string "status", default: "pending", null: false
    t.string "job_id", null: false
    t.string "image_url"
    t.integer "num_inference_steps", default: 30
    t.decimal "guidance_scale", precision: 3, scale: 1, default: "7.5"
    t.integer "width", default: 512
    t.integer "height", default: 512
    t.integer "seed"
    t.jsonb "metadata", default: {}
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["job_id"], name: "index_images_on_job_id", unique: true
    t.index ["status"], name: "index_images_on_status"
    t.index ["user_id", "created_at"], name: "index_images_on_user_id_and_created_at"
    t.index ["user_id"], name: "index_images_on_user_id"
  end

  create_table "users", force: :cascade do |t|
    t.string "email", default: "", null: false
    t.string "encrypted_password", default: "", null: false
    t.string "reset_password_token"
    t.datetime "reset_password_sent_at"
    t.datetime "remember_created_at"
    t.integer "subscription_tier", default: 0, null: false
    t.integer "generation_quota", default: 10, null: false
    t.integer "generations_today", default: 0, null: false
    t.date "quota_reset_date"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["email"], name: "index_users_on_email", unique: true
    t.index ["reset_password_token"], name: "index_users_on_reset_password_token", unique: true
  end

  add_foreign_key "images", "users"
end
