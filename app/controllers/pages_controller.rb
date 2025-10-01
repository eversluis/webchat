class PagesController < ApplicationController
  def home
    if params[:new_chat]
      session.delete(:conversation_id)
    end
  end

  def about
  end

  def contact
  end
end
