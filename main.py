# =============================================================================
# FILE: main.py
# PURPOSE:
#   FastAPI backend for the Fundi Construction Cost Estimator agent.
#   Handles user queries and returns agent responses + generated HTML reports.
# =============================================================================

import os
import sys
import glob
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel
from dotenv import load_dotenv

# Import ADK components
from google.adk.runners import Runner
from google.genai.types import Content, Part
from utils.supabase_session_service import SupabaseSessionService
from utils.memory_manager import MemoryManager, ConversationMemory, WindowBasedCompaction

# Import Estimate Delivery System
from estimate_delivery import generate_simple_pdf, handle_estimate_workflow

# Import the agent
# Ensure the agents directory is in the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agents.website_builder_simple.agent import root_agent

# Load environment variables
load_dotenv()

# =============================================================================
# APP CONFIGURATION
# =============================================================================

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Fundi Construction Estimator API",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://eris.co.ke"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# DATA MODELS
# =============================================================================

class ConstructionQuery(BaseModel):
    user_input: str
    email: Optional[str] = None

class SessionStatsResponse(BaseModel):
    session_id: str
    stats: dict

# =============================================================================
# STATE MANAGEMENT
# =============================================================================

# Initialize session service with Supabase credentials
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("⚠️ WARNING: SUPABASE_URL or SUPABASE_KEY not set in .env file")
    print("Supabase session service will not work without these credentials.")

session_service = SupabaseSessionService(
    supabase_url=supabase_url,
    supabase_key=supabase_key
)
APP_NAME = "fundi_construction_estimator"

# Initialize memory manager with window-based compaction
# Keeps last 15 messages, compacts when > 100 messages or > 50KB
memory_manager = MemoryManager(
    compaction_strategy=WindowBasedCompaction(recent_messages=15, max_history=100)
)
conversation_memory = ConversationMemory(session_service=session_service)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_latest_html_report():
    """
    Finds the most recently created HTML file in the output directory.
    Returns the content of the file if it was created very recently.
    """
    try:
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        list_of_files = glob.glob(os.path.join(output_dir, "*.html"))
        
        if not list_of_files:
            return None
            
        # Get the latest file
        latest_file = max(list_of_files, key=os.path.getctime)
        
        # Read the content
        with open(latest_file, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading latest report: {e}")
        return None

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "Fundi Construction Estimator API",
        "version": "1.0.0",
        "features": {
            "memory_management": "enabled",
            "session_persistence": "Supabase",
            "memory_compaction": "window-based (15 recent messages)"
        },
        "endpoints": {
            "consult": "POST /api/consult-fundi",
            "session_stats": "GET /api/session-stats/{session_id}"
        }
    }

@app.get("/api/session-stats/{session_id}")
async def get_session_stats(session_id: str):
    """
    Get memory statistics for a session.
    Shows conversation analytics, topics, and memory status.
    """
    try:
        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=session_id,
            session_id=session_id
        )
        
        stats = conversation_memory.get_memory_stats(session)
        
        return {
            "status": "success",
            "session_id": session_id,
            "memory_stats": stats
        }
    except Exception as e:
        print(f"Error getting session stats: {e}")
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

@app.post("/api/consult-fundi")
@limiter.limit("5/minute")
async def consult_fundi(query: ConstructionQuery, request: Request):
    """
    Endpoint to consult the Fundi agent.
    Accepts a construction query and returns the agent's response.
    Automatically manages conversation memory with Supabase persistence.
    """
    try:
        # Use email as session_id if provided, else default to a generic one
        session_id = query.email if query.email else "anonymous_user"
        user_id = session_id  # Use same ID for user and session for simplicity
        
        # Check if session exists, if not create it
        try:
            session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id
            )
            print(f"✅ Retrieved existing session: {session_id}")
            
            # Update user details if provided in the query
            if query.name or query.email:
                await session_service.update_session(
                    session, 
                    user_name=query.name, 
                    user_email=query.email
                )
                
        except Exception:
            # Session doesn't exist, create a new one
            print(f"✨ Creating new session for {session_id}")
            session = await session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
                user_name=query.name,
                user_email=query.email
            )
        
        # Get history prepared for LLM (with memory optimization)
        optimized_history = await conversation_memory.get_optimized_history(session)
        print(f"📝 Session history size: {len(optimized_history)} messages")
        
        # Initialize runner with the session service
        runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service
        )
        
        # Capture the number of files before running to detect new ones
        output_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(output_dir, exist_ok=True)
        files_before = set(glob.glob(os.path.join(output_dir, "*.html")))

        # Format the user input as a Content object (required by Google ADK)
        new_message = Content(role="user", parts=[Part(text=query.user_input)])
        
        # Manually track conversation history since Runner isn't persisting it correctly
        # Add user message to history
        current_history = session.state.get("history", []) if session.state else []
        
        # IMPORTANT: We must pass the FULL history to the runner/agent if we want context
        # But Runner.run_async only takes new_message.
        # The LlmAgent in ADK usually maintains history in the session state if configured correctly.
        # Since we are manually managing history in session.state['history'], we need to ensure
        # the agent sees it.
        
        # For now, let's append the new message to our local history tracking
        current_history.append(new_message)
        
        # Run the agent using run_async with proper parameters
        # Note: We are relying on the Runner to use the session we passed in constructor
        # But if Runner doesn't use session.state['history'], we might need to inject it.
        # However, standard ADK Runner should use the session provided.
        events = runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message
        )
        
        # Extract the final response from the event stream
        fundi_response = ""
        
        async for event in events:
            # Check if this is the final response from the agent
            if hasattr(event, "is_final_response") and event.is_final_response():
                if hasattr(event, "content") and hasattr(event.content, "parts"):
                    fundi_response = event.content.parts[0].text
                    # Add agent response to history
                    agent_message = Content(role="model", parts=[Part(text=fundi_response)])
                    current_history.append(agent_message)
                    break
        
        print(f"🔄 Run complete, manually updating session history...")
        
        # Update session with new history
        session.state = {"history": current_history}
        
        # Log the history status
        print(f"📊 Updated session state has {len(current_history)} messages")
        
        # Manually save/update session in Supabase to ensure persistence
        print(f"💾 Manually updating session in Supabase...")
        await session_service.update_session(session)
        
        # Use the updated session for the response
        updated_session = session
        
        # === AUTO-SEND ESTIMATE ===
        if query.email and query.name:
            print(f"📧 Attempting to send estimate to {query.email}...")
            
            # 1. Prepare data for the PDF
            # We truncate the response if it's too long for the table
            display_text = fundi_response[:1000] + "..." if len(fundi_response) > 1000 else fundi_response
            
            estimate_items = [
                {"item": "Consultation", "description": "AI Construction Consultation", "cost": "0.00"},
                {"item": "Summary", "description": display_text, "cost": ""} 
            ]
            
            # 2. Generate PDF (Run in thread to avoid blocking)
            pdf_bytes = await asyncio.to_thread(
                generate_simple_pdf,
                client_data={"name": query.name, "email": query.email, "project": "Consultation"},
                estimate_items=estimate_items
            )
            
            # 3. Send Workflow (Run in background task)
            if pdf_bytes:
                print(f"📄 PDF generated ({len(pdf_bytes)} bytes). Starting background delivery task...")
                asyncio.create_task(
                    asyncio.to_thread(
                        handle_estimate_workflow, 
                        query.email, 
                        query.name, 
                        pdf_bytes
                    )
                )
            else:
                print("❌ PDF generation failed, skipping email delivery.")
        # ==========================

        # Check for new HTML report
        files_after = set(glob.glob(os.path.join(output_dir, "*.html")))
        new_files = files_after - files_before
        
        html_report = None
        if new_files:
            # If multiple files generated, take the latest one
            latest_new_file = max(new_files, key=os.path.getctime)
            try:
                with open(latest_new_file, "r", encoding="utf-8") as f:
                    html_report = f.read()
            except Exception as e:
                print(f"Error reading generated report: {e}")

        # Get final history count
        final_history = updated_session.state.get("history", []) if updated_session.state else []
        
        return {
            "status": "success",
            "fundi_response": fundi_response,
            "html_report": html_report,
            "session_info": {
                "session_id": session_id,
                "messages_in_history": len(final_history),
                "memory_optimized": memory_manager.should_trigger_compaction(final_history)
            }
        }

    except Exception as e:
        print(f"Error in consult-fundi: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)