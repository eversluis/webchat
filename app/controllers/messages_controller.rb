class MessagesController < ApplicationController
  before_action :set_conversation
  
  def create
    @message = @conversation.messages.build(message_params)
    @message.sender = 'user'
    
    # Check for empty content
    if @message.content.blank?
      head :unprocessable_entity
      return
    end

    if @message.save
      # Call Python backend
      bot_response = call_ai_backend(@message.content, @conversation.thread_id)
      
      # Save bot response
      @bot_message = @conversation.messages.create!(
        content: @message.content,
        sender: 'bot',
        response: bot_response
      )
      
      respond_to do |format|
        format.turbo_stream
      end
    else
      Rails.logger.error "Message save failed: #{@message.errors.full_messages}"
      head :unprocessable_entity
    end
  end
  
  private
  
  def set_conversation
    @conversation = Conversation.find(params[:conversation_id])
  end
  
  def message_params
    params.require(:message).permit(:content)
  end
  
  def call_ai_backend(message, thread_id)
    require 'net/http'
    require 'json'
    
    uri = URI('http://localhost:5000/api/chat')
    http = Net::HTTP.new(uri.host, uri.port)
    
    request = Net::HTTP::Post.new(uri)
    request['Content-Type'] = 'application/json'
    request.body = { message: message, thread_id: thread_id }.to_json
    
    response = http.request(request)
    JSON.parse(response.body)['response']
  rescue => e
    Rails.logger.error "AI Backend Error: #{e.message}"
    "Sorry, I'm having trouble connecting right now."
  end
end
