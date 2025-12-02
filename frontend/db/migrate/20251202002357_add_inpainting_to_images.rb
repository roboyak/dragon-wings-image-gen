class AddInpaintingToImages < ActiveRecord::Migration[7.1]
  def change
    add_column :images, :parent_image_id, :integer
    add_index :images, :parent_image_id
  end
end
