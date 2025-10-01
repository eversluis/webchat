class ConversationsController < ApplicationController
  def show
    @conversation = Conversation.find_or_create_by(id: params[:id]) do |conv|
      # Will generate thread_id automatically via callback
    end
    @messages = @conversation.messages.recent
    @message = Message.new
  end
end
