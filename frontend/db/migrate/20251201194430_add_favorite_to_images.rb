class AddFavoriteToImages < ActiveRecord::Migration[7.1]
  def change
    add_column :images, :favorite, :boolean, default: false, null: false
  end
end
