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
import re
import json
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, EmailStr
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

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = exc.errors()
    print(f"❌ VALIDATION ERROR on {request.url.path}:")
    print(f"   Details: {error_details}")
    try:
        body = await request.json()
        print(f"   Received Body: {json.dumps(body, indent=2)}")
    except:
        print("   Could not read body")
        
    return JSONResponse(
        status_code=422,
        content={"detail": error_details},
    )

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://eris.co.ke",
    "https://www.eris.co.ke",
    "https://paulwakoli.me",
    "https://www.paulwakoli.me"
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
    name: Optional[str] = None
    phone: Optional[str] = None

class EstimateData(BaseModel):
    client_name: Optional[str] = None
    project_title: str
    items: List[Dict]
    total_cost: Optional[str] = None
    cost_per_sqm: Optional[str] = None

class EstimateGenerationRequest(BaseModel):
    session_id: Optional[str] = None
    name: Optional[str] = None
    client_name: Optional[str] = None
    email: Optional[str] = None
    estimate_data: EstimateData

    @property
    def final_name(self):
        return self.name or self.client_name or self.estimate_data.client_name or "Valued Client"

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

@app.post("/api/generate-estimate")
@limiter.limit("5/minute")
async def generate_estimate(payload: EstimateGenerationRequest, request: Request):
    """
    Dedicated endpoint to generate and email the PDF estimate.
    Triggered manually by the user from the frontend.
    """
    try:
        print(f"📄 Manual PDF Generation requested...")
        
        # Resolve Name and Email from Session if missing
        final_email = payload.email
        final_name = payload.final_name
        
        # If email is missing or invalid, try to fetch from session
        if not final_email or "@" not in final_email:
            session_id_to_use = payload.session_id or payload.email # Fallback to email field if it holds session_id
            
            if session_id_to_use:
                print(f"🔍 Fetching session data for: {session_id_to_use}")
                try:
                    session = await session_service.create_session(
                        app_name=APP_NAME,
                        session_id=session_id_to_use
                    )
                    # Note: create_session actually gets existing if it exists
                    
                    if session:
                        if not final_email and session.user_email:
                            final_email = session.user_email
                            print(f"   ✅ Found email in session: {final_email}")
                        
                        # Update name if it's just "Valued Client"
                        if final_name == "Valued Client" and session.user_name:
                            final_name = session.user_name
                            print(f"   ✅ Found name in session: {final_name}")
                except Exception as e:
                    print(f"   ⚠️ Could not fetch session: {e}")

        # Final Validation
        if not final_email or "@" not in final_email:
             raise HTTPException(status_code=400, detail="Email address is required. Please provide it or ensure your session is active.")

        print(f"🚀 Generating PDF for {final_name} <{final_email}>")

        # Extract data from the nested object
        project_title = payload.estimate_data.project_title
        items = payload.estimate_data.items
        
        # 1. Generate PDF
        pdf_bytes = await asyncio.to_thread(
            generate_simple_pdf,
            client_data={
                "name": final_name, 
                "email": final_email, 
                "project": project_title
            },
            estimate_items=items
        )
        
        # 2. Send Workflow (Background)
        if pdf_bytes:
            asyncio.create_task(
                asyncio.to_thread(
                    handle_estimate_workflow, 
                    final_email, 
                    final_name, 
                    pdf_bytes
                )
            )
            return {"status": "success", "message": f"Estimate sent to {final_email}"}
        else:
            raise HTTPException(status_code=500, detail="PDF generation failed")
            
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error in generate-estimate: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
                # === FIX: Also save to session.state so it's accessible in Python ===
                if session.state is None:
                    session.state = {}
                if query.name:
                    session.state["user_name"] = query.name
                if query.email:
                    session.state["user_email"] = query.email
                # ===================================================================
                
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
            # === FIX: Initialize state with user details ===
            if session.state is None:
                session.state = {}
            if query.name:
                session.state["user_name"] = query.name
            if query.email:
                session.state["user_email"] = query.email
            # ===============================================
        
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

        # === INJECT CONTEXT (FIXED) ===
        # If we know the user's name/email from the session, tell the Agent silently.
        user_text = query.user_input
        context_note = ""
        
        # 1. Try to get from attributes (safely)
        s_name = getattr(session, "user_name", None)
        s_email = getattr(session, "user_email", None)
        
        # 2. Fallback: Try to get from state (where we just saved it)
        if not s_name and session.state:
            s_name = session.state.get("user_name")
        if not s_email and session.state:
            s_email = session.state.get("user_email")
            
        if s_name or s_email:
            name_str = s_name or "Valued Client"
            email_str = s_email or "unknown"
            context_note = (
                f"[System Note: The user is logged in as {name_str} ({email_str}). "
                f"If they ask for a report, DO NOT ask for their email again. "
                f"Instead, immediately generate the <ESTIMATE_DATA> block so the 'Email Report' button appears.]"
            )
            
        if context_note:
            # Prepend context to the user's message so the Agent sees it
            print(f"🧠 Injecting context: {context_note}")
            user_text = f"{context_note}\n\n{query.user_input}"
        # ==============================

        # Format the user input as a Content object (required by Google ADK)
        # We use the modified user_text for the Agent to see
        new_message = Content(role="user", parts=[Part(text=user_text)])
        
        # Manually track conversation history since Runner isn't persisting it correctly
        # Add user message to history
        # NOTE: We store the ORIGINAL user input in history to keep it clean for the user
        # But we send the MODIFIED input to the runner.
        # However, since ADK Runner might use the history we pass, we have a dilemma.
        # For now, let's store the modified version so the context persists in memory too.
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
        if session.state is None:
            session.state = {}
        session.state["history"] = current_history
        
        # === PERSISTENCE: Re-save user details to session.state ===
        # Ensure user details persist across updates
        if s_name:
            session.state["user_name"] = s_name
        if s_email:
            session.state["user_email"] = s_email
        # ===========================================================
        
        # Log the history status
        print(f"📊 Updated session state has {len(current_history)} messages")
        
        # Manually save/update session in Supabase to ensure persistence
        print(f"💾 Manually updating session in Supabase...")
        await session_service.update_session(session)
        
        # Use the updated session for the response
        updated_session = session
        
        # === ESTIMATE DATA DETECTION (CLIENT-SIDE TRIGGER) ===
        estimate_data = None
        show_estimate_button = False
        
        if "<ESTIMATE_DATA>" in fundi_response:
            print(f"📧 Estimate Data detected! Preparing structured response...")
            try:
                # 1. Extract JSON Data from the tag
                match = re.search(r'<ESTIMATE_DATA>(.*?)</ESTIMATE_DATA>', fundi_response, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()
                    estimate_data = json.loads(json_str)
                    show_estimate_button = True
                    
                    # 2. Clean the response (Remove XML block)
                    fundi_response = re.sub(r"<ESTIMATE_DATA>.*?</ESTIMATE_DATA>", "", fundi_response, flags=re.DOTALL).strip()
                    
                    # 3. Clean up leftover markdown code fences
                    # Remove empty ```xml ``` or ``` ``` blocks
                    fundi_response = re.sub(r"```xml\s*```", "", fundi_response).strip()
                    fundi_response = re.sub(r"```\s*```", "", fundi_response).strip()
                    # Remove any standalone ``` that might be left
                    fundi_response = re.sub(r"```\w*\s*\n?\s*```", "", fundi_response).strip()
                    # Clean up multiple newlines left behind
                    fundi_response = re.sub(r"\n{3,}", "\n\n", fundi_response).strip()
                else:
                    print("⚠️ <ESTIMATE_DATA> tag found but regex failed to extract content.")
            except Exception as e:
                print(f"❌ Error processing estimate data: {e}")
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
            "estimate_data": estimate_data,
            "show_estimate_button": show_estimate_button,
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
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)