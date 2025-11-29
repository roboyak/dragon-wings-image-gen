class AddModelKeyToImages < ActiveRecord::Migration[7.1]
  def change
    add_column :images, :model_key, :string
  end
end
