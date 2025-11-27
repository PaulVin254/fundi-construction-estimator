# =============================================================================
# FILE: api_server.py
# PURPOSE:
#   Flask API server for the Construction Cost Estimator agent with retry logic.
#   Provides REST endpoints for integration with web frontends.
# =============================================================================

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import asyncio
from dotenv import load_dotenv
from typing import Dict, Any

# Import ADK components
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

# Import agent and tools
from agents.website_builder_simple.agent import root_agent

# Import retry configuration
from utils.retry_config import with_retry, API_RETRY_CONFIG, get_user_friendly_error

# Load environment variables
load_dotenv()

# =============================================================================
# FLASK APP SETUP
# =============================================================================

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Configure app
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

session_service = InMemorySessionService()
APP_NAME = "construction_cost_estimator"

# Store runner instances per session (in production, use Redis/DB)
runners: Dict[str, Runner] = {}


def get_or_create_runner(session_id: str) -> Runner:
    """
    Get existing runner or create new one for session.
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        Runner instance
    """
    if session_id not in runners:
        runners[session_id] = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service,
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
    return runners[session_id]


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'Construction Cost Estimator API',
        'version': '1.0.0'
    })


@app.route('/api/estimate', methods=['POST'])
@with_retry(API_RETRY_CONFIG)
def get_estimate():
    """
    Get construction cost estimate from user query.
    
    Request Body:
        {
            "message": "User's construction query",
            "session_id": "optional-session-id",
            "user_id": "optional-user-id"
        }
    
    Response:
        {
            "success": true,
            "response": "Agent's response text",
            "session_id": "session-123",
            "metadata": {
                "model": "gemini-2.0-flash-001",
                "timestamp": "2025-11-19T10:30:00"
            }
        }
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Request must be JSON'
            }), 400
        
        data = request.json
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        # Get session details
        session_id = data.get('session_id', f'session-{os.urandom(8).hex()}')
        user_id = data.get('user_id', 'default-user')
        
        # Get or create runner for this session
        runner = get_or_create_runner(session_id)
        
        # Format message for agent
        new_message = Content(role="user", parts=[Part(text=user_message)])
        
        # Run agent asynchronously with retry logic
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_agent():
            events = runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=new_message
            )
            
            final_response = ""
            async for event in events:
                if hasattr(event, "author") and event.is_final_response():
                    final_response = event.content.parts[0].text
                    break
            
            return final_response
        
        response_text = loop.run_until_complete(run_agent())
        loop.close()
        
        # Return successful response
        return jsonify({
            'success': True,
            'response': response_text,
            'session_id': session_id,
            'metadata': {
                'model': 'gemini-2.0-flash-001',
                'timestamp': __import__('datetime').datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        # Handle errors gracefully
        error_msg = get_user_friendly_error(e)
        app.logger.error(f"Error processing estimate: {str(e)}")
        
        return jsonify({
            'success': False,
            'error': error_msg,
            'technical_error': str(e) if app.debug else None
        }), 500


@app.route('/api/session/clear', methods=['POST'])
def clear_session():
    """
    Clear a specific session or all sessions.
    
    Request Body:
        {
            "session_id": "optional-session-id"  # If omitted, clears all
        }
    """
    try:
        data = request.json or {}
        session_id = data.get('session_id')
        
        if session_id:
            # Clear specific session
            if session_id in runners:
                del runners[session_id]
                message = f"Session {session_id} cleared"
            else:
                message = f"Session {session_id} not found"
        else:
            # Clear all sessions
            runners.clear()
            message = "All sessions cleared"
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/session/list', methods=['GET'])
def list_sessions():
    """List all active sessions."""
    return jsonify({
        'success': True,
        'sessions': list(runners.keys()),
        'count': len(runners)
    })


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ ERROR: GOOGLE_API_KEY not found in environment variables")
        print("Please create a .env file with your API key:")
        print("GOOGLE_API_KEY=your_key_here")
        exit(1)
    
    # Run development server
    print("🚀 Starting Construction Cost Estimator API Server...")
    print("📍 API Endpoints:")
    print("   - POST /api/estimate       - Get cost estimate")
    print("   - GET  /api/health         - Health check")
    print("   - POST /api/session/clear  - Clear sessions")
    print("   - GET  /api/session/list   - List active sessions")
    print("\n✨ Server running with retry logic and graceful error handling\n")
    
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )
