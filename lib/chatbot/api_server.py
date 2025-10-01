from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
import os
import uuid
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chat.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for Rails frontend

# Configure rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Store active conversation threads
conversation_threads = {}

def create_chatbot():
    """Create a chatbot using LangChain, Groq, and LangGraph"""
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env file")
    
    # Initialize Groq model
    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        api_key=api_key,
        temperature=0.7,
        timeout=30,  # 30 second timeout
    )
    
    # Define the chatbot node
    def chatbot_node(state: MessagesState):
        messages = state["messages"]
        if len(messages) == 1:
            system_msg = ("system", "You are a helpful AI assistant. Be concise and friendly.")
            messages = [system_msg] + messages
        
        response = llm.invoke(messages)
        return {"messages": [response]}
    
    # Create the graph
    workflow = StateGraph(MessagesState)
    workflow.add_node("chatbot", chatbot_node)
    workflow.set_entry_point("chatbot")
    workflow.set_finish_point("chatbot")
    
    # Add memory
    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)
    
    return graph

# Initialize chatbot once
try:
    chatbot_graph = create_chatbot()
    logger.info("Chatbot initialized successfully")
except Exception as e:
    logger.error(f"Error initializing chatbot: {e}")
    chatbot_graph = None

@app.route('/api/chat', methods=['POST'])
@limiter.limit("10 per minute")
def chat():
    """Handle chat messages from the Rails frontend"""
    start_time = datetime.now()
    
    if not chatbot_graph:
        logger.error("Chatbot not initialized")
        return jsonify({"error": "Chatbot not initialized"}), 500
    
    try:
        data = request.json
        
        if not data:
            logger.warning("No JSON data received")
            return jsonify({"error": "No data provided"}), 400
        
        message = data.get('message', '').strip()
        thread_id = data.get('thread_id', 'default')
        
        # Validate message
        if not message:
            logger.warning("Empty message received")
            return jsonify({"error": "No message provided"}), 400
        
        if len(message) > 2000:
            logger.warning(f"Message too long: {len(message)} characters")
            return jsonify({"error": "Message too long (max 2000 characters)"}), 400
        
        logger.info(f"Chat request - Thread: {thread_id}, Message length: {len(message)}")
        
        # Configure thread
        config = {"configurable": {"thread_id": thread_id}}
        
        # Get response from chatbot
        response_text = ""
        for event in chatbot_graph.stream(
            {"messages": [("user", message)]},
            config,
            stream_mode="values"
        ):
            last_message = event["messages"][-1]
            if hasattr(last_message, 'content') and last_message.type == 'ai':
                response_text = last_message.content
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Response generated in {duration:.2f}s for thread {thread_id}")
        
        return jsonify({
            "response": response_text,
            "thread_id": thread_id
        })
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"Error in chat after {duration:.2f}s: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/new_thread', methods=['POST'])
def new_thread():
    """Create a new conversation thread"""
    try:
        thread_id = str(uuid.uuid4())
        logger.info(f"New thread created: {thread_id}")
        return jsonify({"thread_id": thread_id})
    except Exception as e:
        logger.error(f"Error creating thread: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to create thread"}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "chatbot_ready": chatbot_graph is not None,
        "timestamp": datetime.now().isoformat()
    })

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit errors"""
    logger.warning(f"Rate limit exceeded: {get_remote_address()}")
    return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

@app.errorhandler(500)
def internal_error_handler(e):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {str(e)}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    logger.info("Starting Flask API server...")
    logger.info("Backend will run on http://localhost:5000")
    logger.info("Make sure your GROQ_API_KEY is set in .env file")
    
    # Check if API key is set
    if not os.getenv("GROQ_API_KEY"):
        logger.error("GROQ_API_KEY not found in .env file!")
        logger.error("Please create a .env file with your API key")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
