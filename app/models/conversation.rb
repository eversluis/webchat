class Conversation < ApplicationRecord
  has_many :messages, dependent: :destroy
  
  before_create :generate_thread_id
  
  private
  
  def generate_thread_id
    self.thread_id = SecureRandom.uuid
  end
end
