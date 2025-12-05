class AddLoraKeyToImages < ActiveRecord::Migration[7.1]
  def change
    add_column :images, :lora_key, :string
    add_index :images, :lora_key
  end
end
