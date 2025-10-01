class CreateConversations < ActiveRecord::Migration[8.0]
  def change
    create_table :conversations do |t|
      t.string :thread_id

      t.timestamps
    end
  end
end
