class Message < ApplicationRecord
  belongs_to :conversation

  validates :content, presence: true
  validates :sender, inclusion: { in: %w[user bot] }

  scope :recent, -> { order(:created_at) }
end
