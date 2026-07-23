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
import uuid
import urllib.parse
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, EmailStr, ValidationError, Field
from dotenv import load_dotenv

# Import ADK components
from google.adk.runners import Runner
from google.genai.types import Content, Part
from utils.supabase_session_service import SupabaseSessionService
from utils.memory_manager import MemoryManager, ConversationMemory, WindowBasedCompaction

# Import Estimate Delivery System
from estimate_delivery import generate_professional_pdf, generate_simple_pdf, handle_estimate_workflow

# Import the agent
# Ensure the agents directory is in the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agents.fundi_estimator.agent import root_agent

# Load environment variables
load_dotenv()

def setup_azure_workload_identity():
    """
    Dynamically configures GCP Workload Identity Federation for Azure Container Apps.
    Azure Container Apps provides IDENTITY_ENDPOINT and IDENTITY_HEADER in container environment.
    """
    identity_endpoint = os.getenv("IDENTITY_ENDPOINT")
    identity_header = os.getenv("IDENTITY_HEADER")
    
    if identity_endpoint and identity_header:
        token_url = f"{identity_endpoint}?api-version=2019-08-01&resource=https://management.azure.com/"
        config = {
            "type": "external_account",
            "audience": "//iam.googleapis.com/projects/155019856232/locations/global/workloadIdentityPools/azure-pool/providers/azure-provider",
            "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
            "token_url": "https://sts.googleapis.com/v1/token",
            "service_account_impersonation_url": "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/fundi-vertex-sa@project-b0fdb974-1817-4454-927.iam.gserviceaccount.com:generateAccessToken",
            "credential_source": {
                "url": token_url,
                "headers": {
                    "X-IDENTITY-HEADER": identity_header
                },
                "format": {
                    "type": "json",
                    "subject_token_field_name": "access_token"
                }
            }
        }
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gcp-credential-config.json")
        try:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config_path
            print(f"✅ Dynamic Azure Workload Identity Configured: {config_path}")
        except Exception as e:
            print(f"⚠️ Could not write GCP credential config: {e}")

setup_azure_workload_identity()

# =============================================================================
# APP CONFIGURATION
# =============================================================================

def get_user_identifier(request: Request) -> str:
    """Extract user identifier from headers, fallback to IP address."""
    user_id = request.headers.get("x-user-id") or request.headers.get("x-session-id")
    if user_id:
        return user_id
    return get_remote_address(request)

# Initialize Rate Limiter with a global app-level throttle (100 total requests per minute)
limiter = Limiter(key_func=get_user_identifier, default_limits=["100/minute"])

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
    "http://localhost:8080",
    "http://localhost:5173",
    "https://eris.co.ke",
    "https://www.eris.co.ke",
    "https://paulwakoli.me",
    "https://www.paulwakoli.me",
    "https://stfundiestimatorweb.z28.web.core.windows.net",
    "http://stfundiestimatorweb.z28.web.core.windows.net"
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
    user_input: str = Field(..., max_length=2000, description="The prompt from the user")
    session_id: str = Field(..., max_length=100, pattern=r"^[a-zA-Z0-9_\-]+$")
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=25, pattern=r"^\+?[0-9\s\-\(\)]+$")

class EstimateItem(BaseModel):
    item: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    cost: str = Field(..., max_length=50)

class EstimateData(BaseModel):
    client_name: Optional[str] = Field(None, max_length=150)
    client_email: Optional[str] = Field(None, max_length=250)
    project_title: str = Field(..., max_length=250)
    items: List[EstimateItem] = Field(..., max_length=200)
    total_cost: Optional[str] = Field(None, max_length=50)
    cost_per_sqm: Optional[str] = Field(None, max_length=50)

class EstimateGenerationRequest(BaseModel):
    session_id: Optional[str] = Field(None, max_length=100)
    name: Optional[str] = Field(None, max_length=150)
    client_name: Optional[str] = Field(None, max_length=150)
    email: Optional[str] = Field(None, max_length=250)
    estimate_data: EstimateData

    @property
    def final_name(self):
        return self.name or self.client_name or self.estimate_data.client_name or "Valued Client"

    @property
    def final_email(self):
        return self.email or self.estimate_data.client_email

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
        final_email = payload.final_email
        final_name = payload.final_name
        
        # If email is missing or invalid, try to fetch from session
        if not final_email or "@" not in final_email:
            session_id_to_use = payload.session_id or payload.email # Fallback to email field if it holds session_id
            
            if session_id_to_use:
                print(f"🔍 Fetching session data for: {session_id_to_use}")
                try:
                    session = await session_service.create_session(
                        app_name=APP_NAME,
                        user_id=session_id_to_use,
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

        # Final Validation (Email is now optional for WhatsApp flow)
        if not final_email or "@" not in final_email:
             print("ℹ️ No email address provided or found. Skipping email delivery.")
             final_email = None

        print(f"🚀 Generating PDF for {final_name} (Email: {final_email or 'None'})")

        # Generate unique estimate reference at handler level
        estimate_reference = "ERIS-" + datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()

        # Extract data from the nested object
        project_title = payload.estimate_data.project_title
        
        # FIX: Convert Pydantic models into dictionaries for the PDF generator
        raw_items = payload.estimate_data.items
        items = [item.model_dump() if hasattr(item, "model_dump") else item.dict() for item in raw_items]
        
        # 1. Generate PDF (Use professional template if WeasyPrint available)
        pdf_bytes = await asyncio.to_thread(
            generate_professional_pdf,
            client_data={
                "name": final_name, 
                "email": final_email or "N/A", 
                "project": project_title,
                "estimate_reference": estimate_reference
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
                    pdf_bytes,
                    estimate_reference
                )
            )
            
            # Construct WhatsApp pre-filled link
            whatsapp_number = os.getenv("FUNDI_WHATSAPP_NUMBER", "254727838624").replace("+", "").strip()
            whatsapp_text = f"Hi Fundi, please send my estimate {estimate_reference}"
            encoded_text = urllib.parse.quote(whatsapp_text)
            whatsapp_link = f"https://wa.me/{whatsapp_number}?text={encoded_text}"
            
            # Construct deterministic Supabase Storage PDF URL
            pdf_url = f"{supabase_url}/storage/v1/object/public/estimates/{estimate_reference}.pdf"
            
            response_msg = f"Estimate generated successfully with reference {estimate_reference}."
            if final_email:
                response_msg += f" Email sent to {final_email}."
            else:
                response_msg += " Available for WhatsApp delivery."
                
            return {
                "status": "success",
                "message": response_msg,
                "estimate_reference": estimate_reference,
                "pdf_url": pdf_url,
                "whatsapp_link": whatsapp_link
            }
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
        session_id = query.session_id
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
            if query.name or query.email or query.phone:
                await session_service.update_session(
                    session, 
                    user_name=query.name, 
                    user_email=query.email,
                    user_phone=query.phone
                )
                # === FIX: Also save to session.state so it's accessible in Python ===
                if session.state is None:
                    session.state = {}
                if query.name:
                    session.state["user_name"] = query.name
                if query.email:
                    session.state["user_email"] = query.email
                if query.phone:
                    session.state["user_phone"] = query.phone
                # ===================================================================
                
        except Exception:
            # Session doesn't exist, create a new one
            print(f"✨ Creating new session for {session_id}")
            session = await session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
                user_name=query.name,
                user_email=query.email,
                user_phone=query.phone
            )
            # === FIX: Initialize state with user details ===
            if session.state is None:
                session.state = {}
            if query.name:
                session.state["user_name"] = query.name
            if query.email:
                session.state["user_email"] = query.email
            if query.phone:
                session.state["user_phone"] = query.phone
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
        # --- SECURITY PATCH: Truncate and frame the user query to prevent prompt injection ---
        safe_query = query.user_input.strip()[:2000]
        context_note = ""
        
        # 1. Try to get from attributes (safely)
        s_name = getattr(session, "user_name", None)
        s_email = getattr(session, "user_email", None)
        s_phone = getattr(session, "user_phone", None)
        
        # 2. Fallback: Try to get from state (where we just saved it)
        if not s_name and session.state:
            s_name = session.state.get("user_name")
        if not s_email and session.state:
            s_email = session.state.get("user_email")
        if not s_phone and session.state:
            s_phone = session.state.get("user_phone")
            
        if s_name or s_email or s_phone:
            name_str = s_name or "Valued Client"
            email_str = s_email or ("whatsapp" if s_phone else "unknown")
            phone_str = s_phone or "unknown"
            
            if s_phone:
                context_note = (
                    f"[System Note: The user is logged in as {name_str} ({email_str}), phone: {phone_str}. "
                    f"The user wants their estimate delivered via WhatsApp. "
                    f"DO NOT ask for their email address or say you cannot send it on WhatsApp. "
                    f"Instead, immediately generate the <ESTIMATE_DATA> block with \"client_email\": \"whatsapp\" in the JSON, "
                    f"so the 'Get PDF on WhatsApp' button renders on their screen.]"
                )
            else:
                context_note = (
                    f"[System Note: The user is logged in as {name_str} ({email_str}). "
                    f"The user wants their estimate delivered via Email. "
                    f"DO NOT ask for their details again. "
                    f"Instead, immediately generate the <ESTIMATE_DATA> block with their actual email in \"client_email\" in the JSON, "
                    f"so the 'Email Report' button renders.]"
                )
            
        if context_note:
            # Prepend context to the user's message so the Agent sees it
            print(f"🧠 Injecting context: {context_note}")
            user_text = f"{context_note}\n\nUser Request: {safe_query}"
        else:
            user_text = f"User Request: {safe_query}"
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
        if s_phone:
            session.state["user_phone"] = s_phone
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
        request_lead_info = False

        if "<REQUEST_LEAD_INFO>" in fundi_response:
            print("👤 Lead info requested by AI...")
            request_lead_info = True
            fundi_response = fundi_response.replace("<REQUEST_LEAD_INFO>", "").strip()
        
        print(f"🔍 Checking for ESTIMATE_DATA in response...")
        print(f"   Response length: {len(fundi_response)} chars")
        print(f"   Contains '<ESTIMATE_DATA>': {'<ESTIMATE_DATA>' in fundi_response}")
        
        if "<ESTIMATE_DATA>" in fundi_response:
            print(f"📧 Estimate Data detected! Preparing structured response...")
            try:
                # 1. Extract JSON Data from the tag
                match = re.search(r'<ESTIMATE_DATA>(.*?)</ESTIMATE_DATA>', fundi_response, re.DOTALL)
                if match:
                    json_str = match.group(1).strip()
                    print(f"   Extracted JSON length: {len(json_str)} chars")
                    raw_data = json.loads(json_str)
                    
                    try:
                        # Validate the raw parsed JSON against our Pydantic schema
                        validated_model = EstimateData(**raw_data)
                        estimate_data = validated_model.model_dump()
                        show_estimate_button = True
                        print(f"   ✅ JSON parsed AND validated successfully. show_estimate_button = {show_estimate_button}")
                        
                        # Fix: Make sure session has recent captured client info
                        extracted_name = validated_model.client_name
                        extracted_email = validated_model.client_email
                        
                        if extracted_name or extracted_email:
                            print(f"   💾 Found user details in payload: name={extracted_name}, email={extracted_email}")
                            
                            if updated_session.state is None:
                                updated_session.state = {}
                            if extracted_name:
                                updated_session.state["user_name"] = extracted_name
                            if extracted_email:
                                updated_session.state["user_email"] = extracted_email
                            
                            # Use update_session kwargs instead of setting attributes directly
                            await session_service.update_session(
                                updated_session, 
                                user_name=extracted_name or getattr(updated_session, 'user_name', None),
                                user_email=extracted_email or getattr(updated_session, 'user_email', None)
                            )

                    except ValidationError as ve:
                        print(f"❌ Pydantic Validation Error on structured response: {ve}")
                        # Reject malformed content with a safe 422 Unprocessable Entity
                        raise HTTPException(
                            status_code=422, 
                            detail="The agent generated an invalid estimate format. Please try again."
                        )
                    
                    # 2. Clean the response (Remove XML block)
                    original_length = len(fundi_response)
                    fundi_response = re.sub(r"<ESTIMATE_DATA>.*?</ESTIMATE_DATA>", "", fundi_response, flags=re.DOTALL).strip()
                    print(f"   Cleaned response: {original_length} -> {len(fundi_response)} chars")
                    
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
        else:
            print(f"   ℹ️ No ESTIMATE_DATA block found in response.")
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
            "request_lead_info": request_lead_info,
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

@app.post("/api/consult-fundi-stream")
@limiter.limit("5/minute")
async def consult_fundi_stream(query: ConstructionQuery, request: Request):
    """
    Streaming endpoint to consult the Fundi agent via Server-Sent Events (SSE).
    Emits real-time tokens as they are generated and final metadata upon completion.
    """
    try:
        session_id = query.session_id
        user_id = session_id
        
        try:
            session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id
            )
            if query.name or query.email or query.phone:
                await session_service.update_session(
                    session, 
                    user_name=query.name, 
                    user_email=query.email,
                    user_phone=query.phone
                )
                if session.state is None:
                    session.state = {}
                if query.name:
                    session.state["user_name"] = query.name
                if query.email:
                    session.state["user_email"] = query.email
                if query.phone:
                    session.state["user_phone"] = query.phone
        except Exception:
            session = await session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
                user_name=query.name,
                user_email=query.email,
                user_phone=query.phone
            )
            if session.state is None:
                session.state = {}
            if query.name:
                session.state["user_name"] = query.name
            if query.email:
                session.state["user_email"] = query.email
            if query.phone:
                session.state["user_phone"] = query.phone

        runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service
        )

        safe_query = query.user_input.strip()[:2000]
        context_note = ""
        
        s_name = getattr(session, "user_name", None) or (session.state.get("user_name") if session.state else None)
        s_email = getattr(session, "user_email", None) or (session.state.get("user_email") if session.state else None)
        s_phone = getattr(session, "user_phone", None) or (session.state.get("user_phone") if session.state else None)

        if s_name or s_email or s_phone:
            name_str = s_name or "Valued Client"
            email_str = s_email or ("whatsapp" if s_phone else "unknown")
            phone_str = s_phone or "unknown"
            
            if s_phone:
                context_note = (
                    f"[System Note: The user is logged in as {name_str} ({email_str}), phone: {phone_str}. "
                    f"The user wants their estimate delivered via WhatsApp. "
                    f"DO NOT ask for their email address or say you cannot send it on WhatsApp. "
                    f"Instead, immediately generate the <ESTIMATE_DATA> block with \"client_email\": \"whatsapp\" in the JSON, "
                    f"so the 'Get PDF on WhatsApp' button renders on their screen.]"
                )
            else:
                context_note = (
                    f"[System Note: The user is logged in as {name_str} ({email_str}). "
                    f"The user wants their estimate delivered via Email. "
                    f"DO NOT ask for their details again. "
                    f"Instead, immediately generate the <ESTIMATE_DATA> block with their actual email in \"client_email\" in the JSON, "
                    f"so the 'Email Report' button renders.]"
                )
            
        user_text = f"{context_note}\n\nUser Request: {safe_query}" if context_note else f"User Request: {safe_query}"
        new_message = Content(role="user", parts=[Part(text=user_text)])

        current_history = session.state.get("history", []) if session.state else []
        current_history.append(new_message)

        async def event_generator():
            fundi_response = ""
            events = runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=new_message
            )

            async for event in events:
                if hasattr(event, "is_final_response") and event.is_final_response():
                    if hasattr(event, "content") and hasattr(event.content, "parts") and event.content.parts:
                        full_text = event.content.parts[0].text
                        # Compute remaining delta if full text was emitted at end
                        if len(full_text) > len(fundi_response):
                            delta = full_text[len(fundi_response):]
                            fundi_response = full_text
                            yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"
                        else:
                            fundi_response = full_text
                elif hasattr(event, "content") and hasattr(event.content, "parts") and event.content.parts:
                    chunk = event.content.parts[0].text
                    if chunk and chunk != fundi_response:
                        if len(chunk) > len(fundi_response) and chunk.startswith(fundi_response):
                            delta = chunk[len(fundi_response):]
                            fundi_response = chunk
                            yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"
                        elif not fundi_response.startswith(chunk):
                            fundi_response += chunk
                            yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

            # Update session history
            agent_message = Content(role="model", parts=[Part(text=fundi_response)])
            current_history.append(agent_message)
            if session.state is None:
                session.state = {}
            session.state["history"] = current_history
            if s_name:
                session.state["user_name"] = s_name
            if s_email:
                session.state["user_email"] = s_email
            if s_phone:
                session.state["user_phone"] = s_phone
            await session_service.update_session(session)

            # Process structured estimate data
            estimate_data = None
            show_estimate_button = False
            request_lead_info = False

            cleaned_response = fundi_response
            if "<REQUEST_LEAD_INFO>" in cleaned_response:
                request_lead_info = True
                cleaned_response = cleaned_response.replace("<REQUEST_LEAD_INFO>", "").strip()

            if "<ESTIMATE_DATA>" in cleaned_response:
                try:
                    match = re.search(r'<ESTIMATE_DATA>(.*?)</ESTIMATE_DATA>', cleaned_response, re.DOTALL)
                    if match:
                        json_str = match.group(1).strip()
                        raw_data = json.loads(json_str)
                        validated_model = EstimateData(**raw_data)
                        estimate_data = validated_model.model_dump()
                        show_estimate_button = True

                        extracted_name = raw_data.get("client_name") or raw_data.get("name")
                        extracted_email = raw_data.get("client_email") or raw_data.get("email")
                        if extracted_name or extracted_email:
                            if session.state is None:
                                session.state = {}
                            if extracted_name:
                                session.state["user_name"] = extracted_name
                            if extracted_email:
                                session.state["user_email"] = extracted_email
                            await session_service.update_session(
                                session,
                                user_name=extracted_name or getattr(session, 'user_name', None),
                                user_email=extracted_email or getattr(session, 'user_email', None)
                            )
                        cleaned_response = re.sub(r"<ESTIMATE_DATA>.*?</ESTIMATE_DATA>", "", cleaned_response, flags=re.DOTALL).strip()
                except Exception as e:
                    print(f"Error parsing estimate data in stream: {e}")

            cleaned_response = re.sub(r"```xml\s*```", "", cleaned_response).strip()
            cleaned_response = re.sub(r"```\s*```", "", cleaned_response).strip()
            cleaned_response = re.sub(r"```\w*\s*\n?\s*```", "", cleaned_response).strip()
            cleaned_response = re.sub(r"\n{3,}", "\n\n", cleaned_response).strip()

            done_payload = {
                "type": "done",
                "fundi_response": cleaned_response,
                "estimate_data": estimate_data,
                "show_estimate_button": show_estimate_button,
                "request_lead_info": request_lead_info
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        print(f"Error in consult-fundi-stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)