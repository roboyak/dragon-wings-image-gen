class AddImg2ImgToImages < ActiveRecord::Migration[7.1]
  def change
    add_column :images, :init_image_url, :string
    add_column :images, :strength, :decimal, precision: 3, scale: 2
    add_column :images, :generation_type, :string, default: 'text_to_image', null: false
    add_index :images, :generation_type
  end
end
